"""Local Telegram adapter for the existing CRM graph."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

from crm.graph import build_graph
from crm.providers.groq import GroqSearchAnswerer
from crm.storage import FIELDS, SQLiteContactStore

LOGGER = logging.getLogger(__name__)
HELP_MESSAGE = (
    "Send one business-card photo or JPEG/PNG image document in this private chat. "
    "A name caption is optional. Then send one voice note or /done to continue "
    "without voice.\n\nSearch with /search your question, or send /search and then your question."
)
CARD_RECEIVED_MESSAGE = "Card received.\n\nSend one voice note, or /done to continue without voice."
NO_PENDING_MESSAGE = (
    "No business-card intake is waiting. Send a business-card image with the "
    "person's name in its caption first."
)
MISSING_CAPTION_MESSAGE = "✗ Input rejected\n\nAdd the person's name as the image caption and send it again."
UNSUPPORTED_MESSAGE = (
    "✗ Input rejected\n\nSend one business-card photo or JPEG/PNG image document."
)
GROUP_MESSAGE = "This bot only works in private chats."
UNAUTHORIZED_MESSAGE = "You are not authorized to use this bot."
DOWNLOAD_ERROR_MESSAGE = "✗ Image download failed\n\nPlease send the business-card image again."
VOICE_DOWNLOAD_ERROR_MESSAGE = "✗ Voice download failed\n\nPlease send the voice note again, or /done."
GENERIC_ERROR_MESSAGE = "✗ Something went wrong\n\nPlease try again."
STORE_ERROR_MESSAGE = "✗ Contact could not be stored\n\nPlease try again."
SEARCH_PROMPT_MESSAGE = "What would you like to find?"
NO_RESULTS_MESSAGE = "No matching contacts found."
SEARCH_ERROR_MESSAGE = "✗ Search failed\n\nPlease try again."
_SUPPORTED_DOCUMENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
_RESULT_KEYS = ("status", "errors", "contact_evidence", "voice_transcript", "conversation_notes")
_TELEGRAM_CHUNK_UNITS = 3500


@dataclass(frozen=True)
class TelegramBotConfig:
    token: str
    allowed_user_ids: frozenset[int]
    db_path: str = "crm.sqlite3"


@dataclass(frozen=True)
class PendingIntake:
    name: str | None
    directory: tempfile.TemporaryDirectory
    image_path: str


def load_config(environ: Mapping[str, str] | None = None) -> TelegramBotConfig:
    values = os.environ if environ is None else environ
    token = values.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    raw_ids = values.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
    if not raw_ids:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS is required")
    try:
        allowed_ids = frozenset(int(value.strip()) for value in raw_ids.split(","))
    except ValueError as exc:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS must contain numeric IDs") from exc
    if not allowed_ids:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS must not be empty")
    return TelegramBotConfig(token, allowed_ids, values.get("CRM_DB_PATH", "crm.sqlite3"))


async def _deny_access(update, allowed_user_ids) -> bool:
    message = update.effective_message
    if update.effective_chat is None or update.effective_chat.type != "private":
        await message.reply_text(GROUP_MESSAGE)
        return True
    if update.effective_user is None or update.effective_user.id not in allowed_user_ids:
        await message.reply_text(UNAUTHORIZED_MESSAGE)
        return True
    return False


def _safe_graph_errors(errors) -> list[str]:
    safe = []
    for error in errors if isinstance(errors, list) else []:
        normalized = str(error).lower()
        if "name" in normalized and "required" in normalized:
            message = "name is required"
        elif "image" in normalized or "card" in normalized:
            message = "image could not be validated"
        elif "voice" in normalized:
            message = "voice note could not be validated"
        else:
            message = "input could not be validated"
        if message not in safe:
            safe.append(message)
    return safe or ["input could not be validated"]


def _project_result(result) -> dict | None:
    if not isinstance(result, Mapping):
        return None
    projected = {key: result.get(key) for key in _RESULT_KEYS}
    projected["errors"] = [] if not result.get("errors") else _safe_graph_errors(result.get("errors"))
    try:
        json.dumps(projected, ensure_ascii=False)
        return projected
    except (TypeError, ValueError):
        return None


def _format_contact(result: Mapping) -> str:
    if result.get("status") != "complete":
        errors = _safe_graph_errors(result.get("errors"))
        return "✗ Input could not be processed\n\n" + "\n".join(errors)
    evidence = result.get("contact_evidence") or {}
    labels = {
        "full_name": "👤 Name", "company": "🏢 Company", "job_title": "💼 Role",
        "email": "📧 Email", "phone": "📱 Phone", "website": "🌐 Website",
        "address": "📍 Address",
    }
    lines = ["✅ Contact processed", "", "Status: complete"]
    for field in FIELDS:
        value = evidence.get(field)
        if value is not None and str(value).strip():
            lines.append(f"{labels[field]}: {value}")
    notes = result.get("conversation_notes")
    if notes is not None and str(notes).strip():
        lines.extend(["", "🎙 Conversation notes", str(notes)])
    return "\n".join(lines)


def _message_chunks(text: str):
    """Split without data loss, staying below Telegram's UTF-16 text limit."""
    start = units = 0
    for index, character in enumerate(text):
        width = 2 if ord(character) > 0xFFFF else 1
        if units + width > _TELEGRAM_CHUNK_UNITS:
            yield text[start:index]
            start, units = index, 0
        units += width
    if start < len(text):
        yield text[start:]


def build_handlers(allowed_user_ids: set[int] | frozenset[int], graph=None, store=None, answerer=None):
    allowed = frozenset(allowed_user_ids)
    crm_graph = build_graph() if graph is None else graph
    contact_store = SQLiteContactStore(os.getenv("CRM_DB_PATH", "crm.sqlite3")) if store is None else store
    search_answerer = answerer
    pending: dict[int, PendingIntake] = {}
    pending_searches: set[int] = set()

    def cleanup(chat_id: int) -> None:
        intake = pending.pop(chat_id, None)
        if intake:
            intake.directory.cleanup()

    async def help_handler(update, context) -> None:
        if not await _deny_access(update, allowed):
            await update.effective_message.reply_text(HELP_MESSAGE)

    async def unsupported_handler(update, context) -> None:
        if not await _deny_access(update, allowed):
            await update.effective_message.reply_text(UNSUPPORTED_MESSAGE)

    async def intake_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        message = update.effective_message
        if message.media_group_id is not None:
            await message.reply_text(UNSUPPORTED_MESSAGE)
            return
        caption = (message.caption or "").strip() or None
        attachment, suffix = None, ".jpg"
        if message.photo:
            attachment = message.photo[-1]
        elif message.document is not None:
            suffix = _SUPPORTED_DOCUMENT_TYPES.get(message.document.mime_type, "")
            if suffix:
                attachment = message.document
        if attachment is None:
            await message.reply_text(UNSUPPORTED_MESSAGE)
            return

        directory = tempfile.TemporaryDirectory(prefix="crm-telegram-")
        image_path = Path(directory.name) / f"business-card{suffix}"
        try:
            telegram_file = await attachment.get_file(connect_timeout=15, read_timeout=30)
            await telegram_file.download_to_drive(custom_path=image_path, connect_timeout=15, read_timeout=60)
        except Exception as exc:
            directory.cleanup()
            LOGGER.error("Telegram image download failed (%s)", type(exc).__name__)
            await message.reply_text(DOWNLOAD_ERROR_MESSAGE)
            return
        chat_id = update.effective_chat.id
        cleanup(chat_id)
        pending[chat_id] = PendingIntake(caption, directory, str(image_path))
        await message.reply_text(CARD_RECEIVED_MESSAGE)

    async def finish(update, voice_path: str | None) -> None:
        chat_id = update.effective_chat.id
        intake = pending.get(chat_id)
        if intake is None:
            await update.effective_message.reply_text(NO_PENDING_MESSAGE)
            return
        try:
            result = crm_graph.invoke({
                "name": intake.name, "image_path": intake.image_path,
                "voice_path": voice_path, "status": "pending", "errors": [],
            })
            projected = _project_result(result)
            if projected is None:
                LOGGER.error("CRM graph returned an invalid result")
                await update.effective_message.reply_text(GENERIC_ERROR_MESSAGE)
            else:
                output = json.dumps(projected, indent=2, ensure_ascii=False)
                print(output, flush=True)
                if projected.get("status") == "complete":
                    try:
                        contact_store.save(update.effective_user.id, projected)
                    except Exception as exc:
                        LOGGER.error("SQLite contact persistence failed (%s)", type(exc).__name__)
                        await update.effective_message.reply_text(STORE_ERROR_MESSAGE)
                        return
                formatted = _format_contact(projected)
                for chunk in _message_chunks(formatted):
                    await update.effective_message.reply_text(chunk)
        except Exception as exc:
            LOGGER.error("CRM graph invocation failed (%s)", type(exc).__name__)
            await update.effective_message.reply_text(GENERIC_ERROR_MESSAGE)
        finally:
            cleanup(chat_id)

    async def voice_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        chat_id = update.effective_chat.id
        intake = pending.get(chat_id)
        if intake is None:
            await update.effective_message.reply_text(NO_PENDING_MESSAGE)
            return
        voice_path = Path(intake.directory.name) / "voice.ogg"
        try:
            telegram_file = await update.effective_message.voice.get_file(connect_timeout=15, read_timeout=30)
            await telegram_file.download_to_drive(custom_path=voice_path, connect_timeout=15, read_timeout=60)
        except Exception as exc:
            voice_path.unlink(missing_ok=True)
            LOGGER.error("Telegram voice download failed (%s)", type(exc).__name__)
            await update.effective_message.reply_text(VOICE_DOWNLOAD_ERROR_MESSAGE)
            return
        await finish(update, str(voice_path))

    async def done_handler(update, context) -> None:
        if not await _deny_access(update, allowed):
            await finish(update, None)

    async def search_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        chat_id = update.effective_chat.id
        text = (update.effective_message.text or "").strip()
        query = text.partition(" ")[2].strip()
        pending_searches.discard(chat_id)
        if not query:
            pending_searches.add(chat_id)
            await update.effective_message.reply_text(SEARCH_PROMPT_MESSAGE)
            return
        await run_search(update, query)

    async def run_search(update, query: str) -> None:
        try:
            records = contact_store.search(update.effective_user.id, query, limit=5)
            if not records:
                await update.effective_message.reply_text(NO_RESULTS_MESSAGE)
                return
            active_answerer = search_answerer or GroqSearchAnswerer.from_env()
            answer = active_answerer.answer(query, records)
            for chunk in _message_chunks("🔎 Search result\n\n" + answer):
                await update.effective_message.reply_text(chunk)
        except Exception as exc:
            LOGGER.error("CRM search failed (%s)", type(exc).__name__)
            await update.effective_message.reply_text(SEARCH_ERROR_MESSAGE)

    async def text_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        chat_id = update.effective_chat.id
        if chat_id in pending_searches:
            query = (update.effective_message.text or "").strip()
            if not query:
                await update.effective_message.reply_text(SEARCH_PROMPT_MESSAGE)
                return
            pending_searches.discard(chat_id)
            await run_search(update, query)
        else:
            await update.effective_message.reply_text(UNSUPPORTED_MESSAGE)

    return SimpleNamespace(help=help_handler, intake=intake_handler, voice=voice_handler,
                           done=done_handler, search=search_handler, text=text_handler,
                           unsupported=unsupported_handler, pending=pending,
                           pending_searches=pending_searches)


def create_application(config: TelegramBotConfig, graph=None, store=None, answerer=None):
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    if store is None:
        store = SQLiteContactStore(config.db_path)
    callbacks = build_handlers(config.allowed_user_ids, graph, store, answerer)
    application = Application.builder().token(config.token).build()
    application.add_handler(CommandHandler(["start", "help"], callbacks.help))
    application.add_handler(CommandHandler("done", callbacks.done))
    application.add_handler(CommandHandler("search", callbacks.search))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, callbacks.intake))
    application.add_handler(MessageHandler(filters.VOICE, callbacks.voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, callbacks.text))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, callbacks.unsupported))
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    config = load_config()
    create_application(config).run_polling()


if __name__ == "__main__":
    main()
