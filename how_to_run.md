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
- `langsmith` — optional tracing and offline `evaluate()`
- `discord.py` — optional Discord DM adapter (`python -m crm.discord_bot`)
- `pytest` — test runner
- the `crm` CLI entry point (optional; see below)

---

## 4. Run the tests

From the project root:

```bash
pytest -q
```

The default suite excludes live provider tests (`addopts = -m "not live"`). It injects a **FakeEmbedder** (and fake card/voice providers). It does not need a network connection, `GROQ_API_KEY`, or `LANGSMITH_API_KEY`, never constructs the live embedder, and never uploads traces or experiment results.

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

`LANGSMITH_API_KEY` is **optional**. When it is set, `enable_tracing()` turns on LangSmith tracing (`LANGSMITH_TRACING=true`, project `ai-conference-crm`) so live Groq extract/transcribe/embed spans nest under the graph invoke. Without the key, tracing is a no-op and nothing is uploaded.

---

## 5b. Offline evaluation

Run the capture graph against the checked-in dataset (fake providers, temp SQLite — no LangSmith account required):

```bash
python -m crm.eval
```

This writes `eval/latest_experiment.json` with per-example evaluator scores and means. If `LANGSMITH_API_KEY` is present, the same command also uploads the experiment and records the URL in that file. Default `pytest` stays offline and never needs a LangSmith key.

---

## 6. Run the CLI

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
```

With optional typed notes (no transcription):

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --notes "Met at AI Tinkerer. Interested in workflow automation."
```

With an optional local voice file (transcribed when the path is a real file):

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --voice input/6134386456120009929.ogg
```

Typed notes and voice can be combined. Merge is deterministic (typed, blank line, then transcript):

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --notes "Potential consulting lead." --voice input/6134386456120009929.ogg
```

Name + image still complete when `--voice` and `--notes` are omitted. Absence of notes is normal success.

Semantic query against stored embeddings (needs `GROQ_API_KEY` and a database that already has contacts). This does **not** run the capture graph:

```bash
python -m crm query "Who did I meet regarding data warehouse consulting?"
```

Same command via the console script:

```bash
crm query "Who did I meet regarding data warehouse consulting?"
```

Default result limit is 5 (`--limit` to change). Output is a ranked text list from SQLite contact rows:

```text
1. Sarah Khan
   NexaTech Solutions
   Director of Product

   Met at LEAP.
   Discussed data warehouse modernization.

2. Omar Rahman
   DataWorks

   Discussed analytics infrastructure.
```

If you installed the package, you can also use:

```bash
crm --name "Sarah Khan" --image input/visiting_card.png
```

The image path must point to an **existing file**. A placeholder file is enough to pass path validation, but only a real card image will extract useful fields.

Successful runs persist a contact to **`data/crm.db`**. A later run with the same normalized email (or phone, or name+company) **updates** that row instead of inserting a second one. New notes are appended. `contact_id` and `crm_action` (`created` or `updated`) are printed in the JSON.

---

## 6b. Discord DM adapter

The Discord bot is **not** a LangGraph node. It maps DMs to the same `{name, image_path, voice_path, typed_notes}` payload as the CLI, or to `query_contacts`. The CLI stays available.

**Token:** set `DISCORD_BOT_TOKEN` in `.env` or the environment (same `GROQ_API_KEY` and `data/crm.db` as the CLI). Gateway connection — no webhook or public URL.

```bash
# .env
DISCORD_BOT_TOKEN=...
GROQ_API_KEY=...
```

In the [Discord Developer Portal](https://discord.com/developers/applications), enable **Message Content Intent** (Privileged Gateway Intents). The bot uses DM messages + `message_content` only.

Invite the bot to your account (or a server if you need the slash command registered), then:

```bash
python -m crm.discord_bot
```

**DM capture**

1. DM a business-card **image**. First line of text = **name**; remaining lines = typed notes.
2. Bot replies that the card was received; send a **voice message** or type `save` (or `done`).
3. Voice (`audio/ogg`, `voice-message.ogg`, or any `audio/*`) is downloaded as-is (no FFmpeg) and the capture graph runs.
4. Extra typed text while waiting is appended to notes. Pending state is in-memory (lost on restart).
5. Image + voice in the first DM runs immediately. Image with no name: bot asks for the name.

**Query** (does not run the capture graph, does not write contacts):

```text
/query Who did I meet regarding data warehouse consulting?
```

Guild/channel messages are ignored. DMs only.

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
| `load_input`          | Copies CLI inputs (`name`, `image_path`, `voice_path`, `typed_notes`) into graph state |
| `validate_input`      | Checks name, image file, optional voice file                            |
| `extract_card`        | Calls `CardExtractor` when input is valid; skips the API when invalid   |
| `validate_extraction` | Validates the raw payload with `ContactEvidence`                        |
| `transcribe_voice`    | Calls `VoiceTranscriber` only when a voice file is present and status is valid |
| `merge_context`       | Deterministic: typed only / voice only / both (`typed\\n\\nvoice`) / neither → `None` |
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
- RAG chat / Telegram, Slack, WhatsApp, or a web UI
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
