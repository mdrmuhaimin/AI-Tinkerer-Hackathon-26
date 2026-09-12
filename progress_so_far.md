# Progress So Far — AI Conference CRM

Last updated: 2026-09-12

This document records only work that has been specified and completed. The next task is not listed here because it has not been specified.

How to run the current app: see [how_to_run.md](how_to_run.md).

---

## What this project is

A small conference CRM capture workflow. The user provides:

- a person's name
- a business-card image
- an optional voice-file path

The system is built as an explicit LangGraph. Deterministic Python handles validation and workflow. Groq is used to read the card image and, when a voice file is present, to transcribe it.

No database, embeddings, Telegram, or contact storage yet.

---

## Task 1 — LangGraph Skeleton

**Status:** Done. Independent verifier PASS.

**What we built:** The smallest runnable graph and CLI. No LLM.

**Graph at the end of Task 1:**

```text
START → load_input → validate_input → finalize → END
```

**CLI:**

```bash
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg --voice /path/to/note.wav
```

**State (`crm/state.py`):** raw inputs plus `status` and `errors`.

**Validation (ordinary Python):**

- Name is required (blank or whitespace fails).
- Image path is required and must be an existing file.
- Voice path is optional; if provided, it must be an existing file.
- Failures set `status="invalid"` and still reach END. They do not crash.

**What Task 1 did not do:** read the card, call an API, or store a contact.

**Key files:** `crm/state.py`, `crm/graph.py`, `crm/cli.py`, `tests/test_graph.py`, `tests/test_cli.py`

---

## Task 2 — Business Card Extraction

**Status:** Done. Independent verifier PASS.

**What we built:** Two new graph nodes. A Pydantic schema. An isolated AI provider. Fake-extractor unit tests plus one optional live smoke test.

**Graph now:**

```text
START → load_input → validate_input → extract_card → validate_extraction → finalize → END
```

Linear edges only. If input validation already failed, `extract_card` returns the state unchanged and does **not** call Groq.

**Schema (`crm/schemas.py` — `ContactEvidence`):**

- `full_name` (required)
- `company`, `job_title`, `email`, `phone`, `website`, `address` (each may be null)

The model is told to return `null` when a field is not visible on the card. Empty optional strings are normalized to `null`. Invalid model JSON fails schema validation (`status="invalid"`). API/provider failure sets `status="error"`.

**Provider isolation:**

```text
LangGraph extract_card  →  CardExtractor.extract_card(path)  →  Groq
                                    ↑
                           tests: FakeExtractor
```

The graph does not contain Groq HTTP details. Tests inject `FakeExtractor`, so default `pytest` never needs a network or API key.

**Live provider:** official Groq Python client (`from groq import Groq`), following Groq vision docs:

- local image encoded as a base64 `data:` URL
- model `qwen/qwen3.6-27b`
- `response_format={"type": "json_object"}`

**API key:** `GROQ_API_KEY` in a local `.env` file (gitignored) or in the system environment. The app loads `.env` with `python-dotenv`. The key is not committed or hardcoded.

**CLI output** now includes `contact_evidence`. Exit `0` on `complete`, `1` on `invalid` or `error`.

**Key files:** `crm/schemas.py`, `crm/providers/base.py`, `crm/providers/groq.py`, `crm/graph.py`, `tests/test_extract.py`, `tests/test_live_extract.py`

---

## Task 3 — Optional Voice Note Branch and Transcription

**Status:** Done. Independent verifier PASS.

**What we built:** An explicit LangGraph fork after card extraction. Voice is optional. Both paths meet at `merge_context`.

**Graph now:**

```text
validate_extraction
        ↓
   voice_present?
      /        \
    no          yes
     |     transcribe_voice
     \        /
    merge_context → finalize → END
```

**State:** `voice_transcript` and `conversation_notes` (both `None` when voice is absent).

**Provider:** `VoiceTranscriber` protocol. Live impl is Groq Whisper `whisper-large-v3`. Original `.ogg` is passed through. No FFmpeg. Tests use `FakeTranscriber`.

**Boundary:** Card fields stay identity. Voice text is conversation context only. Voice never overwrites `company` or other `ContactEvidence` fields.

**CLI:** still `--voice` as a local path. Telegram is not part of this task.

**Key files:** `crm/graph.py` (`voice_present`, `transcribe_voice`, `merge_context`), `crm/providers/base.py`, `crm/providers/groq.py`, `tests/test_voice.py`

---

## Live check on a real card

On branch `ft/Core_Engine`, with `GROQ_API_KEY` in `.env` and `input/visiting_card.png`:

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
```

Result: `status="complete"`. Extracted evidence included name, company (NexaTech Solutions), title, email, phone, website, and address.

---

## Tests

Default (no live API):

```bash
pytest -q
```

Last recorded default run after Task 3: **30 passed, 2 deselected**.

Optional live smoke tests (need `GROQ_API_KEY`; card image and/or `input/6134386456120009929.ogg`):

```bash
pytest -q -m live --override-ini addopts=
```

---

## What is intentionally not built yet

These were not in Task 1, Task 2, or Task 3:

- PostgreSQL or any CRM storage
- Duplicate detection
- Create/update of a stored contact
- Embeddings / semantic search
- Telegram or other chat integrations
- Structured reminders / follow-up extraction from the transcript

---

## Where to look

| Topic | File |
| --- | --- |
| Graph nodes and edges | `crm/graph.py` |
| Shared graph state | `crm/state.py` |
| Contact schema | `crm/schemas.py` |
| Groq client | `crm/providers/groq.py` |
| CLI | `crm/cli.py` |
| How to run | `how_to_run.md` |
| Learning harness | `AGENTS.md` |
