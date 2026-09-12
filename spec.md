# Telegram Input Adapter MVP Specification

## Goal

Add Telegram as a small input/output adapter for the existing CRM graph. The bot
runs on the developer's laptop and lets an approved user submit one business-card
image with the person's name as its caption.

This task does not make Telegram part of LangGraph and does not change the
existing graph, state model, or CLI behavior.

```text
Telegram private message
        ↓
Telegram adapter (access, download, formatting, cleanup)
        ↓
{name, image_path, voice_path=None, status="pending", errors=[]}
        ↓
START → load_input → validate_input → finalize → END
        ↓
Telegram response
```

## Runtime and configuration

- Python 3.11 or newer.
- Current stable asynchronous `python-telegram-bot` API.
- Start with `python -m crm.telegram_bot`.
- Run locally with long polling. There are no webhooks, public server, cloud
  deployment, or Docker requirements.
- Read the bot token from `TELEGRAM_BOT_TOKEN`.
- Read a comma-separated allowlist of numeric Telegram user IDs from
  `TELEGRAM_ALLOWED_USER_IDS`.
- Both variables are required. Secrets must never be committed, shown to users,
  or logged.

## Accepted input

An allowlisted user in a private chat sends exactly one of:

1. A Telegram photo with the person's name as its caption.
2. A JPEG or PNG image document with the person's name as its caption.

The full trimmed caption is the name; the adapter performs no natural-language
parsing. Albums and multi-card submissions are not supported.

For each intake, the adapter creates a separate temporary directory, downloads
the image into it, and invokes the existing graph while the file exists with:

```python
{
    "name": caption.strip(),
    "image_path": downloaded_path,
    "voice_path": None,
    "status": "pending",
    "errors": [],
}
```

The directory is removed after graph execution, including failure paths. There
is no persistent image storage.

## Responses

Successful graph validation returns exactly:

```text
✓ Input accepted

Name: Ada Lovelace
Status: complete
```

A graph validation failure begins with:

```text
✗ Input rejected

```

and includes safe user-facing error text. Local paths and internal details must
not be exposed. A download failure asks the user to resend the image. An
unexpected failure returns a generic try-again response and is logged without
secrets.

`/start` and `/help` explain that the user must send one business-card photo or
JPEG/PNG image document and put only the person's name in the caption.

The bot safely rejects:

- users not in the allowlist;
- group and channel messages;
- photos or supported documents without a caption;
- text without an image;
- unsupported attachments;
- media albums.

## Explicit non-goals

This MVP has no voice-note flow, pending conversation state, OCR, transcription,
database, duplicate detection, persistence, processing indicator, RAG, or
additional graph nodes. `Status: complete` means only that the current graph
accepted the input validation; it does **not** mean a contact was saved.

## Acceptance criteria

- A valid photo and a valid JPEG/PNG document each map to the specified graph
  state, and the downloaded file exists during graph invocation.
- Temporary files are cleaned up after success and failure.
- Access, caption, media type, album, download, validation, and unexpected-error
  paths return safe messages and do not invoke later work when rejected.
- Graph error formatting cannot expose a local file path.
- `/start` and `/help` document the exact input contract.
- Configuration rejects missing tokens, empty allowlists, and nonnumeric IDs.
- Automated tests use fake Telegram updates/files and never contact Telegram.
- Existing graph and CLI tests continue to pass unchanged.
