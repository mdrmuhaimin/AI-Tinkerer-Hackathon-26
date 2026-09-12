from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from crm.db import DEFAULT_DB_PATH, ContactStore
from crm.graph import build_graph
from crm.search import _format_query_hits, query_contacts

log = logging.getLogger(__name__)

_PROMPT_VOICE = "Card received. Send a voice message or type `save`."


@dataclass
class Pending:
    image_path: str
    typed_notes: str | None = None
    voice_path: str | None = None


def _join_notes(old: str | None, extra: str | None) -> str | None:
    if not extra:
        return old
    return extra if not old else f"{old}\n\n{extra}"


def _format_capture(result: dict) -> str:
    ev = result.get("contact_evidence") or {}
    lines = [ev.get("full_name") or result.get("name") or "Unknown"]
    if ev.get("company"):
        lines.append(str(ev["company"]))
    bits = []
    if result.get("crm_action"):
        bits.append(str(result["crm_action"]))
    if result.get("contact_id") is not None:
        bits.append(f"contact_id={result['contact_id']}")
    if bits:
        lines.append(" · ".join(bits))
    notes = result.get("conversation_notes")
    if notes:
        lines.extend(["", str(notes)])
    if result.get("status") != "complete":
        lines.append(f"status: {result.get('status')}")
        lines.extend(result.get("errors") or [])
    return "\n".join(lines)


def is_voice(*, filename: str = "", content_type: str = "") -> bool:
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    return ct.startswith("audio/") or name == "voice-message.ogg"


def is_image(*, filename: str = "", content_type: str = "") -> bool:
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    return ct.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


class Intake:
    def __init__(self, *, download, build_graph, store=None, embedder=None) -> None:
        self.pending: dict[str, Pending] = {}
        self._download = download
        self._build_graph = build_graph
        self._store = store
        self._embedder = embedder

    def handle_message(
        self,
        user_id,
        text: str = "",
        images=None,
        voices=None,
        *,
        is_dm: bool = True,
    ) -> str | None:
        if not is_dm:
            log.info("ignored non-dm user=%s text=%r", user_id, text)
            return None
        return self.handle_dm(user_id, text, images or [], voices or [])

    def handle_query(self, text: str) -> str:
        log.info("query text=%r", text)
        return _format_query_hits(query_contacts(self._store, self._embedder, text))

    def handle_dm(self, user_id, text, images, voices) -> str | None:
        uid = str(user_id)
        body = text or ""
        log.info(
            "dm user=%s text=%r images=%s voices=%s",
            uid,
            body,
            images,
            voices,
        )
        stripped = body.strip()
        if stripped.lower().startswith("/query"):
            return self.handle_query(stripped[6:].strip())

        image = self._download(images[0]) if images else None
        voice = self._download(voices[0]) if voices else None

        if image:
            notes = body.strip() or None
            if voice:
                return self._run(uid, image, voice, notes)
            self.pending[uid] = Pending(
                image_path=image, typed_notes=notes, voice_path=voice
            )
            return _PROMPT_VOICE

        session = self.pending.get(uid)
        if session is None:
            return "Send a business card image first." if voice else None

        if stripped.lower() in {"save", "done"}:
            return self._run(uid, session.image_path, None, session.typed_notes)

        if voice:
            session.voice_path = voice
            return self._run(uid, session.image_path, voice, session.typed_notes)

        if stripped:
            session.typed_notes = _join_notes(session.typed_notes, stripped)
            return "Noted."
        return None

    def _run(
        self, uid: str, image: str, voice: str | None, notes: str | None
    ) -> str:
        result = self._build_graph().invoke(
            {
                "name": None,
                "image_path": image,
                "voice_path": voice,
                "typed_notes": notes,
                "status": "pending",
                "errors": [],
                "contact_evidence": None,
                "extracted_card": None,
                "voice_transcript": None,
                "conversation_notes": None,
                "normalized_contact": None,
                "matched_contact_id": None,
                "contact_id": None,
                "crm_action": None,
                "verified_contact": None,
            }
        )
        self.pending.pop(uid, None)
        return _format_capture(result)


async def _save_attachment(attachment) -> str:
    suffix = Path(attachment.filename or "bin").suffix or ".bin"
    fd, dest = tempfile.mkstemp(prefix="crm-dc-", suffix=suffix)
    os.close(fd)
    await attachment.save(dest)
    return dest


def main() -> None:
    import discord
    from discord import app_commands

    from crm.providers.embeddings import GroqEmbedder

    load_dotenv()
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN is not set")

    embedder = GroqEmbedder.from_env()
    store = ContactStore(DEFAULT_DB_PATH, embedding_dim=embedder.dimension)
    intake = Intake(
        download=lambda path: path,
        build_graph=lambda: build_graph(store=store, embedder=embedder),
        store=store,
        embedder=embedder,
    )

    intents = discord.Intents.default()
    intents.dm_messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @tree.command(name="query", description="Search CRM contacts")
    async def query_cmd(interaction: discord.Interaction, text: str):
        log.info(
            "slash /query user=%s guild=%s text=%r",
            interaction.user.id,
            interaction.guild_id,
            text,
        )
        if interaction.guild is not None:
            await interaction.response.send_message("Use /query in a DM.", ephemeral=True)
            return
        await interaction.response.send_message(intake.handle_query(text))

    @client.event
    async def on_ready():
        log.info("logged in as %s", client.user)
        await tree.sync()

    @client.event
    async def on_message(message: discord.Message):
        if message.author.bot or message.guild is not None:
            return
        log.info(
            "discord message user=%s content=%r attachments=%s",
            message.author.id,
            message.content,
            [
                (att.filename, att.content_type, att.size)
                for att in message.attachments
            ],
        )
        images, voices = [], []
        for att in message.attachments:
            dest = await _save_attachment(att)
            if is_voice(filename=att.filename, content_type=att.content_type or ""):
                voices.append(dest)
            elif is_image(filename=att.filename, content_type=att.content_type or ""):
                images.append(dest)
        reply = intake.handle_message(
            message.author.id, message.content or "", images, voices, is_dm=True
        )
        if reply:
            await message.channel.send(reply)

    client.run(token)


if __name__ == "__main__":
    main()
