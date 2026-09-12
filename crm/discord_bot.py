from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from crm.db import DEFAULT_DB_PATH, ContactStore
from crm.graph import build_graph
from crm.search import _format_query_hits, query_contacts

_PROMPT_NAME = "What is the contact's name?"
_PROMPT_VOICE = "Card received. Send a voice message or type `save`."


@dataclass
class Pending:
    image_path: str
    name: str | None = None
    typed_notes: str | None = None
    voice_path: str | None = None


def _split_caption(text: str) -> tuple[str | None, str | None]:
    if not (text or "").strip():
        return None, None
    first, *rest = text.splitlines()
    name = first.strip() or None
    notes = "\n".join(rest).strip() or None
    return name, notes


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
            return None
        return self.handle_dm(user_id, text, images or [], voices or [])

    def handle_query(self, text: str) -> str:
        return _format_query_hits(query_contacts(self._store, self._embedder, text))

    def handle_dm(self, user_id, text, images, voices) -> str | None:
        uid = str(user_id)
        body = text or ""
        stripped = body.strip()
        if stripped.lower().startswith("/query"):
            return self.handle_query(stripped[6:].strip())

        image = self._download(images[0]) if images else None
        voice = self._download(voices[0]) if voices else None

        if image:
            name, notes = _split_caption(body)
            if name and voice:
                return self._run(uid, name, image, voice, notes)
            self.pending[uid] = Pending(
                image_path=image, name=name, typed_notes=notes, voice_path=voice
            )
            return _PROMPT_VOICE if name else _PROMPT_NAME

        session = self.pending.get(uid)
        if session is None:
            return "Send a business card image first." if voice else None

        if stripped.lower() in {"save", "done"}:
            if not session.name:
                return _PROMPT_NAME
            return self._run(
                uid, session.name, session.image_path, None, session.typed_notes
            )

        if voice:
            session.voice_path = voice
            if not session.name:
                return _PROMPT_NAME
            return self._run(
                uid, session.name, session.image_path, voice, session.typed_notes
            )

        name, notes = _split_caption(body)
        if not name:
            return None
        if session.name is None:
            session.name = name
            session.typed_notes = _join_notes(session.typed_notes, notes)
            if session.voice_path:
                return self._run(
                    uid,
                    session.name,
                    session.image_path,
                    session.voice_path,
                    session.typed_notes,
                )
            return _PROMPT_VOICE

        session.typed_notes = _join_notes(session.typed_notes, stripped)
        return "Noted."

    def _run(self, uid: str, name: str, image: str, voice: str | None, notes: str | None) -> str:
        result = self._build_graph().invoke(
            {
                "name": name,
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
        if interaction.guild is not None:
            await interaction.response.send_message("Use /query in a DM.", ephemeral=True)
            return
        await interaction.response.send_message(intake.handle_query(text))

    @client.event
    async def on_ready():
        await tree.sync()

    @client.event
    async def on_message(message: discord.Message):
        if message.author.bot or message.guild is not None:
            return
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
