# How to Run and Test the AI Conference CRM

The project has three local interfaces: Telegram using long polling on your
laptop, the CLI with optional voice-note transcription, and a semantic
`crm query` command. All of them invoke the same LangGraph. The graph
validates input, extracts structured business-card evidence with Groq,
optionally transcribes a voice file, merges typed notes and the transcript,
normalizes and persists the contact to SQLite (create or update), builds and
stores an embedding for semantic search, and then finishes.

Repeating the same card updates the existing row. The default database is
`data/crm.db`.

## 1. Create a Python 3.11+ environment

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

`python --version` must report Python 3.11 or newer. If `python3.11` is not
installed on macOS with Homebrew, install it with `brew install python@3.11`.
When returning in a new terminal, run `source .venv/bin/activate` again.

This installs:

- `langgraph` — graph orchestration
- `pydantic` — `ContactEvidence` schema
- `groq` — card extract, voice transcription, embeddings
- `sqlite-vec` / `apsw` — local vector KNN (`contact_embeddings`)
- `langsmith` — optional tracing and offline `evaluate()`
- `python-telegram-bot` — the Telegram adapter
- `pytest` — test runner
- the `crm` CLI entry point (optional; see below)

## 2. Configure credentials safely

The Groq key is required for real card extraction, voice transcription, and
embeddings:

```bash
export GROQ_API_KEY="REPLACE_WITH_A_NEW_GROQ_KEY"
```

The key may be set in the system environment or in a local `.env` file
(gitignored). The app loads `.env` via `python-dotenv`; do not put keys in
source files.

For Telegram, also export the BotFather token and private-chat allowlist:

```bash
export TELEGRAM_BOT_TOKEN="REPLACE_WITH_YOUR_TELEGRAM_BOT_TOKEN"
export TELEGRAM_ALLOWED_USER_IDS="111111111"
```

Use comma-separated numeric IDs to allow multiple users. Never put real keys in
source files, commits, screenshots, or shared logs. `.env` and `.env.local` are
gitignored; the Groq provider and CLI load `.env`, while Telegram configuration
is most clearly supplied by exporting all three values in the launching shell.

If a key has been pasted into chat or otherwise exposed, revoke it in the
provider console and create a replacement before continuing.

`LANGSMITH_API_KEY` is **optional**. When it is set, `enable_tracing()` turns
on LangSmith tracing (`LANGSMITH_TRACING=true`, project `ai-conference-crm`)
so live Groq extract/transcribe/embed spans nest under the graph invoke.
Without the key, tracing is a no-op and nothing is uploaded.

## 3. Run automated tests

```bash
pytest -q
```

The default suite excludes tests marked `live` (`addopts = -m "not live"`); it
does not call Groq or Telegram. It injects a **FakeEmbedder** and fake
card/voice providers, so it does not need a network connection,
`GROQ_API_KEY`, or `LANGSMITH_API_KEY`, and never uploads traces or experiment
results.

Run only Telegram tests with:

```bash
pytest -q tests/test_telegram_bot.py
```

Live Groq tests are optional and consume API access:

```bash
pytest -q -m live --override-ini addopts=
```

They require `GROQ_API_KEY` (environment or `.env`) and the sample files under
`input/` (`input/visiting_card.png`; the live voice test also needs
`input/6134386456120009929.ogg` and is skipped if that file is missing).

## 4. Offline evaluation

Run the capture graph against the checked-in dataset (fake providers, temp
SQLite — no LangSmith account required):

```bash
python -m crm.eval
```

This writes `eval/latest_experiment.json` with per-example evaluator scores
and means. If `LANGSMITH_API_KEY` is present, the same command also uploads
the experiment and records the URL in that file. Default `pytest` stays
offline and never needs a LangSmith key.

## 5. Run and manually test Telegram

Start the bot with the environment active and all three variables exported:

```bash
python -m crm.telegram_bot
```

Keep the terminal open and laptop awake. Stop the bot with `Ctrl-C`.

From an allowlisted account in a private chat:

1. Send one business-card photo (or JPEG/PNG document) and put only the person's
   name in its caption.
2. Wait for `Card received.`
3. Send one Telegram voice note, or send `/done` to process the card without voice.

The bot keeps the card only while this intake is pending. Restarting the process
loses pending intakes, so resend the card after a restart.

On successful card extraction and voice transcription, Telegram displays the
complete projected graph result as plain JSON:

```json
{
  "status": "complete",
  "errors": [],
  "contact_evidence": {
    "full_name": "Ada Lovelace",
    "company": null,
    "job_title": null,
    "email": null,
    "phone": null,
    "website": null,
    "address": null
  },
  "voice_transcript": "Met at the conference.",
  "conversation_notes": "Met at the conference."
}
```

With `/done`, `voice_transcript` and `conversation_notes` are `null`.
Long transcripts may make the JSON arrive as several consecutive Telegram
messages; read them in order as one complete result.

Useful manual checks:

| Action | Expected result |
|---|---|
| Send `/start` or `/help` privately | Card, voice, and `/done` instructions |
| Send a supported image without a caption | Missing-caption rejection |
| Send text without an image | Supported-format rejection |
| Send a PDF or album | Supported-format rejection |
| Send voice or `/done` before a card | Instructions to send a card first |
| Send a second card before voice | Old pending card is replaced |
| Voice download temporarily fails | Card remains pending; retry voice or `/done` |
| Message from an unlisted account | Authorization rejection |
| Use the bot in a group | Private-chat-only rejection |

After processing succeeds or fails, temporary card/voice files are deleted.
The Telegram adapter handles access control, media download, formatting, and
cleanup. It is not a graph node.

## 6. Run and manually test the CLI

Card only:

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

Typed notes and voice can be combined. Merge is deterministic (typed, blank
line, then transcript):

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --notes "Potential consulting lead." --voice input/6134386456120009929.ogg
```

Name + image still complete when `--voice` and `--notes` are omitted. Absence
of notes is normal success.

The installed `crm` command is equivalent:

```bash
crm --name "Sarah Khan" --image input/visiting_card.png
```

The image path must point to an **existing file**. A placeholder file is
enough to pass path validation, but only a real card image will extract
useful fields.

Successful runs persist a contact to **`data/crm.db`**. A later run with the
same normalized email (or phone, or name+company) **updates** that row
instead of inserting a second one. New notes are appended. `contact_id` and
`crm_action` (`created` or `updated`) are printed in the JSON.

Semantic query against stored embeddings (needs `GROQ_API_KEY` and a database
that already has contacts). This does **not** run the capture graph:

```bash
python -m crm query "Who did I meet regarding data warehouse consulting?"
```

Same command via the console script:

```bash
crm query "Who did I meet regarding data warehouse consulting?"
```

Default result limit is 5 (`--limit` to change). Output is a ranked text list
from SQLite contact rows:

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

## 7. What the output looks like

On success, the CLI prints the **final graph state as JSON** (including
`contact_evidence`) and exits with code `0`:

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

On validation or extraction failure, it still prints JSON but exits with code
`1` (`status` is `invalid` or `error`).

## 8. What the graph does today

Current flow (conditional voice branch, then persistence and embedding):

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
| `merge_context`       | Deterministic: typed only / voice only / both (`typed\n\nvoice`) / neither → `None` |
| `normalize_contact`   | Deterministic email/phone/name/company forms for matching               |
| `search_crm`          | Looks up an existing row (email, then phone, then name+company)         |
| `create_contact`      | Inserts a new SQLite row when no match                                  |
| `update_contact`      | Updates the matched row; blank new fields do not erase existing values  |
| `verify_write`        | Re-reads the row and checks intended fields                             |
| `build_search_document` | Joins non-blank `full_name`, `company`, `job_title`, `notes`          |
| `create_embedding`    | Isolated embedder → vector (live Groq only when no embedder injected)   |
| `store_embedding`     | Upserts `contact_embeddings` (rowid = contact_id); always replaces      |
| `finalize`            | Sets `status` to `complete` only after verify; embedding errors stay `error` |

If `validate_input` already set `status="invalid"`, `extract_card` returns
the state unchanged and does not call the provider. Prior `invalid`/`error`
status also skips `transcribe_voice`.

The Telegram adapter (section 5) drives the same graph; it is not itself a
graph node.

## 9. What is not implemented yet

The following are intentionally out of scope so far:

- PostgreSQL, SQLAlchemy, or migrations
- RAG chat over Telegram (Telegram supports card capture, not query)
- Reminder / task / follow-up-date extraction from the voice note
- Duplicate detection beyond email/phone/name+company matching

## Troubleshooting

### `ModuleNotFoundError`

Confirm the active interpreter and reinstall:

```bash
source .venv/bin/activate
python --version
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

### Missing environment variable or `status: error`

Export `GROQ_API_KEY` in the same terminal before starting the CLI or Telegram
bot. Telegram also requires `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_ALLOWED_USER_IDS`. Restart the bot after changing variables.

### Telegram does not respond

Confirm the process is still running, the laptop is awake and online, the user
ID is allowed, and no second process is polling the same bot token. This local
setup uses polling, not webhooks.

### No extracted data appears in the terminal for Telegram

The structured result appears in the Telegram chat (the bot console), not the
shell running the polling process. The shell displays operational logs only.
