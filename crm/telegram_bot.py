"""Local Telegram adapter for the existing CRM graph."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

from crm.graph import build_graph

LOGGER = logging.getLogger(__name__)

HELP_MESSAGE = (
    "Send one business-card photo or JPEG/PNG image document in this private "
    "chat. Put only the person's name in the caption.\n\n"
    "Example caption:\nAda Lovelace"
)
MISSING_CAPTION_MESSAGE = (
    "✗ Input rejected\n\n"
    "Add the person's name as the image caption and send it again."
)
UNSUPPORTED_MESSAGE = (
    "✗ Input rejected\n\n"
    "Send one business-card photo or JPEG/PNG image document with the person's "
    "name in the caption."
)
GROUP_MESSAGE = "This bot only works in private chats."
UNAUTHORIZED_MESSAGE = "You are not authorized to use this bot."
DOWNLOAD_ERROR_MESSAGE = (
    "✗ Image download failed\n\nPlease send the business-card image again."
)
GENERIC_ERROR_MESSAGE = "✗ Something went wrong\n\nPlease try again."

_SUPPORTED_DOCUMENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}


@dataclass(frozen=True)
class TelegramBotConfig:
    token: str
    allowed_user_ids: frozenset[int]


def load_config(environ: Mapping[str, str] | None = None) -> TelegramBotConfig:
    """Load required Telegram settings without exposing their values."""
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
    return TelegramBotConfig(token, allowed_ids)


async def _deny_access(update, allowed_user_ids: frozenset[int] | set[int]) -> bool:
    message = update.effective_message
    if update.effective_chat is None or update.effective_chat.type != "private":
        await message.reply_text(GROUP_MESSAGE)
        return True
    if (
        update.effective_user is None
        or update.effective_user.id not in allowed_user_ids
    ):
        await message.reply_text(UNAUTHORIZED_MESSAGE)
        return True
    return False


def _safe_graph_errors(errors: list[str] | None) -> str:
    safe: list[str] = []
    for error in errors or []:
        normalized = str(error).lower()
        if "name" in normalized and "required" in normalized:
            message = "name is required"
        elif "image" in normalized:
            message = "image could not be validated"
        elif "voice" in normalized:
            message = "voice note could not be validated"
        else:
            message = "input could not be validated"
        if message not in safe:
            safe.append(message)
    return "\n".join(safe or ["input could not be validated"])


def build_handlers(allowed_user_ids: set[int] | frozenset[int], graph=None):
    """Build callbacks separately from Telegram registration for easy testing."""
    allowed = frozenset(allowed_user_ids)
    crm_graph = build_graph() if graph is None else graph

    async def help_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        await update.effective_message.reply_text(HELP_MESSAGE)

    async def unsupported_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return
        await update.effective_message.reply_text(UNSUPPORTED_MESSAGE)

    async def intake_handler(update, context) -> None:
        if await _deny_access(update, allowed):
            return

        message = update.effective_message
        if message.media_group_id is not None:
            await message.reply_text(UNSUPPORTED_MESSAGE)
            return

        caption = (message.caption or "").strip()
        if not caption:
            await message.reply_text(MISSING_CAPTION_MESSAGE)
            return

        attachment = None
        suffix = ".jpg"
        if message.photo:
            attachment = message.photo[-1]
        elif message.document is not None:
            suffix = _SUPPORTED_DOCUMENT_TYPES.get(message.document.mime_type, "")
            if suffix:
                attachment = message.document
        if attachment is None:
            await message.reply_text(UNSUPPORTED_MESSAGE)
            return

        with tempfile.TemporaryDirectory(prefix="crm-telegram-") as directory:
            image_path = Path(directory) / f"business-card{suffix}"
            try:
                telegram_file = await attachment.get_file()
                await telegram_file.download_to_drive(custom_path=image_path)
            except Exception as exc:
                LOGGER.error(
                    "Telegram image download failed (%s)", type(exc).__name__
                )
                await message.reply_text(DOWNLOAD_ERROR_MESSAGE)
                return

            try:
                result = crm_graph.invoke(
                    {
                        "name": caption,
                        "image_path": str(image_path),
                        "voice_path": None,
                        "status": "pending",
                        "errors": [],
                    }
                )
            except Exception as exc:
                LOGGER.error("CRM graph invocation failed (%s)", type(exc).__name__)
                await message.reply_text(GENERIC_ERROR_MESSAGE)
                return

            if not isinstance(result, Mapping):
                LOGGER.error("CRM graph returned an invalid result")
                await message.reply_text(GENERIC_ERROR_MESSAGE)
                return

            if result.get("status") == "complete":
                await message.reply_text(
                    f"✓ Input accepted\n\nName: {caption}\nStatus: complete"
                )
            else:
                errors = _safe_graph_errors(result.get("errors"))
                await message.reply_text(f"✗ Input rejected\n\n{errors}")

    return SimpleNamespace(
        help=help_handler,
        intake=intake_handler,
        unsupported=unsupported_handler,
    )


def create_application(config: TelegramBotConfig, graph=None):
    """Register the Telegram-facing routes on an async PTB application."""
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    callbacks = build_handlers(config.allowed_user_ids, graph)
    application = Application.builder().token(config.token).build()
    application.add_handler(CommandHandler(["start", "help"], callbacks.help))
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.ALL, callbacks.intake)
    )
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, callbacks.unsupported)
    )
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Telegram Bot API request URLs contain the token. Keep HTTP request logs
    # below WARNING out of application output even when global INFO logging is on.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    config = load_config()
    create_application(config).run_polling()


if __name__ == "__main__":
    main()
