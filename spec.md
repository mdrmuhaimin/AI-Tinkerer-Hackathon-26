# Telegram Card and Voice Intake Specification

## Goal and boundary

An allowlisted user can submit a business-card image and name through a private
Telegram chat, then send one Telegram voice note or `/done`. Telegram remains an
adapter: it downloads files and invokes the existing optional-voice LangGraph.
There is no database or contact persistence.

```text
photo/JPEG/PNG + name caption → pending intake → voice note or /done
                                                   ↓
load_input → validate_input → extract_card → validate_extraction
                                                   ↓
                                             voice_present?
                                            /              \
                                     transcribe_voice     merge_context
                                            \              /
                                          merge_context → finalize
                                                   ↓
                                       projected JSON reply
```

## Configuration and access

Run locally with Python 3.11+, long polling, and `python -m crm.telegram_bot`.
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, and `GROQ_API_KEY` are
required for live use. Only allowlisted users in private chats may use any
handler. Secrets and provider details must not be logged or returned.

## Conversation

`/start` and `/help` tell the user to send one photo or JPEG/PNG document with
only the person's name in its caption, followed by one voice note or `/done`.

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

Albums, unsupported documents, missing captions, arbitrary audio files, group
messages, and unauthorized users are rejected. Only Telegram's voice-message
type is accepted for the voice step.

## Graph input and output

The adapter invokes the existing graph with the stored name and paths, status
`pending`, and an empty error list. It replies with indented plain JSON containing
exactly these top-level keys. Long JSON is delivered in consecutive, ordered
messages whose bodies concatenate to the complete JSON without truncation:

```json
{
  "status": "complete",
  "errors": [],
  "contact_evidence": {
    "full_name": "...",
    "company": "...",
    "job_title": "...",
    "email": "...",
    "phone": "...",
    "website": "...",
    "address": "..."
  },
  "voice_transcript": "...",
  "conversation_notes": "..."
}
```

The reply never includes local paths, `extracted_card`, API keys, or
provider/internal error detail. Graph errors are reduced to safe categories while
preserving graph status. Invalid or unserializable results and unexpected
exceptions receive a generic error response.

## Acceptance criteria

- Card input queues without graph invocation; voice and `/done` invoke it once.
- Image and voice files exist during graph execution and are then cleaned up.
- JSON has exactly the five specified keys and real graph result values.
- Per-chat isolation, deterministic replacement, retry, and restart behavior are
  explicit and tested where applicable.
- Access, input, download, graph, serialization, and cleanup failure paths are safe.
- Tests use fake Telegram/Groq boundaries and make no live network calls.
- LangGraph, providers, and CLI remain unchanged.

`complete` means extraction and optional transcription completed. It does not
mean a contact was stored.
