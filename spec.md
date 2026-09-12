# Telegram Capture and SQLite FTS Search Specification

## Goal and boundary

An allowlisted user can submit a business-card image with an optional caption
through a private Telegram chat, then send one voice note or `/done`. The graph
extracts, optionally transcribes, deterministically matches, writes, and verifies
the contact in SQLite. Telegram shows readable data and terminal prints JSON.

```text
image + optional caption → voice or /done → capture graph → data/crm.db
                                                            ↓
/search question → SQLite FTS5 (max 5) → grounded Groq answer → Telegram
```

## Configuration and access

Run locally with Python 3.11+, long polling, and `python -m crm.telegram_bot`.
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, and `GROQ_API_KEY` are
required for live use. `CRM_DB_PATH` optionally overrides the single database;
its default is `data/crm.db`. Secrets and provider details are never returned.

## Conversation

`/start` and `/help` tell the user to send one photo or JPEG/PNG document with
an optional name caption, followed by one voice note or `/done`.

A valid card is downloaded with explicit Telegram connection/read timeouts and
stored in an in-memory, per-chat pending intake. The graph is not invoked yet.
The bot replies:

```text
Card received.

Send one voice note, or /done to continue without voice.
```

A voice note from the same chat is downloaded beside the pending image. The
graph is invoked once while both files exist. `/done` invokes it with
`voice_path=None`. Voice or `/done` without a pending card returns safe usage
instructions without invoking the graph.

Sending a new valid card in the same chat replaces and deletes the previous
pending intake. Chats remain isolated. A failed card download creates no new
pending intake; a failed voice download preserves the card so voice can be
retried or skipped. All files and pending state are removed after graph success
or failure. Restarting the local bot loses pending intakes.

Albums, unsupported documents, arbitrary audio files, group
messages, and unauthorized users are rejected. Only Telegram's voice-message
type is accepted for the voice step.

## Graph input and output

The adapter invokes the graph with the optional caption as a name hint. It fills
a missing extracted name but never overwrites a valid extracted name. Telegram
shows a human-readable summary and omits blank fields:

```text
✅ Contact processed

Status: complete
👤 Name: Ada Lovelace
🏢 Company: Analytical Engines

🎙 Conversation notes
Met at LEAP and discussed automation.
```

The terminal prints exactly one sanitized JSON object with `status`, `errors`,
`contact_evidence`, `voice_transcript`, and `conversation_notes`. It excludes
paths, `extracted_card`, API keys, and provider detail.

## Persistence and search

The graph is the only persistence path. `ContactStore` owns both the contacts
table and FTS5 index in one SQLite database. Create and update synchronize the
index transactionally; startup backfills older contacts. Indexed text includes
all contact fields and appended notes. Failure prevents successful completion.

`/search query` and `/search` followed by text tokenize arbitrary input safely,
retrieve at most five FTS matches, and ask `GroqSearchAnswerer` for an answer
grounded only in those rows. Telegram receives only the final answer, never the
model's reasoning. No matches return directly without calling Groq.
This is lexical RAG, not vector retrieval; normal capture never calls a Groq
embeddings endpoint.

## Acceptance criteria

- Card input queues without graph invocation; voice and `/done` invoke it once.
- Image and voice files exist during graph execution and are then cleaned up.
- Telegram is formatted, while terminal JSON has exactly the five safe keys.
- Captionless images are accepted; extracted full name remains authoritative.
- Capture and search share `ContactStore` and `data/crm.db`; no duplicate save.
- FTS is synchronized on create/update, safely backfilled, and capped at five.
- Both search interactions use grounded Groq generation only after retrieval.
- Per-chat isolation, deterministic replacement, retry, and restart behavior are
  explicit and tested where applicable.
- Access, input, download, graph, serialization, and cleanup failure paths are safe.
- Tests use fake Telegram/Groq boundaries and make no live network calls.
- Default capture completes after verified persistence without embeddings.

`complete` means extraction, optional transcription, persistence, and independent
write verification completed.
