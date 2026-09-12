# How to Run — AI Conference CRM (Task 4)

This document describes how to set up and run what has been built so far: the **LangGraph capture graph** with deterministic input validation, business-card extraction, optional voice-note transcription, and SQLite contact create/update.

Repeating the same card updates the existing row. The default database is `data/crm.db`.

---

## Prerequisites

- **Python 3.11 or newer**
- A terminal
- Git (to clone the repo)

Check your Python version:

```bash
python3 --version
```

---

## 1. Get the code

If you have not already cloned the repository:

```bash
git clone https://github.com/mdrmuhaimin/AI-Tinkerer-Hackathon-26.git
cd AI-Tinkerer-Hackathon-26
```

If you already have the repo locally, pull the latest changes:

```bash
git pull
```

---

## 2. Create a virtual environment

From the project root:

```bash
python3 -m venv .venv
```

Activate it:

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Install the package

Install the project in editable mode with dev dependencies (includes pytest):

```bash
pip install -e ".[dev]"
```

This installs:

- `langgraph` — graph orchestration
- `pydantic` — `ContactEvidence` schema
- `groq` — card extract, voice transcription, embeddings
- `sqlite-vec` — local vector KNN (`contact_embeddings`)
- `pytest` — test runner
- the `crm` CLI entry point (optional; see below)

---

## 4. Run the tests

From the project root:

```bash
pytest -q
```

The default suite excludes live provider tests (`addopts = -m "not live"`). It injects a **FakeEmbedder** (and fake card/voice providers). It does not need a network connection or API key and never constructs the live embedder.

---

## 5. Provider environment variables

Live extraction uses the official Groq Python client and reads **only** `GROQ_API_KEY`.

The key may be set in the system environment or in a local `.env` file (gitignored). The app loads `.env` via `python-dotenv`; do not put keys in source files.

```bash
# .env
GROQ_API_KEY=...

# or in the shell
export GROQ_API_KEY=...
```

The vision call follows Groq's documented API: `from groq import Groq`, local image as a base64 `data:` URL, model `qwen/qwen3.6-27b`, and `response_format={"type": "json_object"}`.

Voice transcription uses the same `GROQ_API_KEY` and Groq Speech-to-Text: `client.audio.transcriptions.create(file=..., model="whisper-large-v3")`. The original audio file is sent as-is (ogg is accepted; no FFmpeg or conversion).

If `GROQ_API_KEY` is missing on a live CLI run, card extraction fails with `status: error`. If a voice file was also supplied, a missing key fails transcription the same way after a valid card extract.

---

## 6. Run the CLI

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
```

With an optional local voice file (transcribed when the path is a real file):

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --voice input/6134386456120009929.ogg
```

Name + image still complete when `--voice` is omitted. Absence of a voice note is normal success.

Semantic query against stored embeddings (needs `GROQ_API_KEY` and a database that already has contacts):

```bash
python -m crm query "Who did I meet regarding AI workflow automation?"
```

Same command via the console script:

```bash
crm query "Who did I meet regarding AI workflow automation?"
```

Default result limit is 5 (`--limit` to change). Output is a JSON list of contact rows plus `distance`.

If you installed the package, you can also use:

```bash
crm --name "Sarah Khan" --image input/visiting_card.png
```

The image path must point to an **existing file**. A placeholder file is enough to pass path validation, but only a real card image will extract useful fields.

Successful runs persist a contact to **`data/crm.db`**. A later run with the same normalized email (or phone, or name+company) **updates** that row instead of inserting a second one. New notes are appended. `contact_id` and `crm_action` (`created` or `updated`) are printed in the JSON.

---

## 7. What the output looks like

On success, the CLI prints the **final graph state as JSON** (including `contact_evidence`) and exits with code `0`:

```json
{
  "name": "Ada Lovelace",
  "image_path": "/tmp/card.jpg",
  "voice_path": null,
  "status": "complete",
  "errors": [],
  "contact_evidence": {
    "full_name": "Ada Lovelace",
    "company": "Analytical Engines",
    "job_title": "Mathematician",
    "email": "ada@example.com",
    "phone": "+44 20 0000 0000",
    "website": "https://ada.example",
    "address": "London"
  },
  "voice_transcript": null,
  "conversation_notes": null,
  "contact_id": 1,
  "crm_action": "created"
}
```

On validation or extraction failure, it still prints JSON but exits with code `1` (`status` is `invalid` or `error`).

---

## 8. What the graph does today

Current flow (conditional voice branch):

```text
START → load_input → validate_input → extract_card → validate_extraction
  → voice_present?
       /          \
     no            yes
      |      transcribe_voice
      \          /
       merge_context → persistable?
            /              \
      invalid/error         valid
            |                 |
            |          normalize_contact → search_crm → match_found?
            |                                 /              \
            |                         update_contact    create_contact
            |                                 \              /
            \                         verify_write → write_ok?
             \                              /              \
              \                     write_failed         write_ok
               \                           |                 |
                \                          |    build_search_document
                 \                         |    → create_embedding
                  \                        |    → store_embedding
                   \                       \                 /
                    \                       finalize → END
```

| Node                  | Purpose                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| `load_input`          | Copies CLI inputs into graph state                                      |
| `validate_input`      | Checks name, image file, optional voice file                            |
| `extract_card`        | Calls `CardExtractor` when input is valid; skips the API when invalid   |
| `validate_extraction` | Validates the raw payload with `ContactEvidence`                        |
| `transcribe_voice`    | Calls `VoiceTranscriber` only when a voice file is present and status is valid |
| `merge_context`       | Copies a non-empty transcript into `conversation_notes`                 |
| `normalize_contact`   | Deterministic email/phone/name/company forms for matching               |
| `search_crm`          | Looks up an existing row (email, then phone, then name+company)         |
| `create_contact`      | Inserts a new SQLite row when no match                                  |
| `update_contact`      | Updates the matched row; blank new fields do not erase existing values  |
| `verify_write`        | Re-reads the row and checks intended fields                             |
| `build_search_document` | Joins non-blank `full_name`, `company`, `job_title`, `notes`          |
| `create_embedding`    | Isolated embedder → vector (live Groq only when no embedder injected)   |
| `store_embedding`     | Upserts `contact_embeddings` (rowid = contact_id); always replaces      |
| `finalize`            | Sets `status` to `complete` only after verify; embedding errors stay `error` |

If `validate_input` already set `status="invalid"`, `extract_card` returns the state unchanged and does not call the provider. Prior `invalid`/`error` status also skips `transcribe_voice`.

---

## 9. Live tests

Requires `GROQ_API_KEY` (environment or `.env`) and `input/visiting_card.png`. The live voice test also needs `input/6134386456120009929.ogg`; it is skipped if that file is missing.

Because the default pytest config is `-m "not live"`, override it:

```bash
pytest -q -m live --override-ini addopts=
```

The live tests are skipped unless `GROQ_API_KEY` is set. Default `pytest` never constructs a live Groq client.

---

## 10. What is not implemented yet

The following are intentionally out of scope for this task:

- PostgreSQL, SQLAlchemy, or migrations
- RAG chat / Telegram or other chat integrations
- Reminder / task / follow-up-date extraction from the voice note

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'crm'`**

- Activate the virtual environment and run `pip install -e ".[dev]"` again.

**`image file not found`**

- Use an absolute path or a path relative to your current directory.
- Confirm the file exists: `ls -l /path/to/card.jpg`

**`status: error` and missing environment variables**

- Set `GROQ_API_KEY` in `.env` or export it in your shell before a live run.

**Tests fail after pulling new code**

```bash
pip install -e ".[dev]"
pytest -q
```
