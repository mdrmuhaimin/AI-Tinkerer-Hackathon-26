# How to Run and Test the AI Conference CRM

The project has two local interfaces: Telegram using long polling on your
laptop, and the CLI with optional voice-note transcription. Both invoke the
same LangGraph. The graph validates input, extracts structured business-card
evidence with Groq, optionally transcribes a voice file, and then finishes. It
does not save contacts to a database.

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

## 2. Configure credentials safely

The Groq key is required for real card extraction and voice transcription:

```bash
export GROQ_API_KEY="REPLACE_WITH_A_NEW_GROQ_KEY"
```

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

## 3. Run automated tests

```bash
pytest -q
```

The default suite excludes tests marked `live`; it does not call Groq or
Telegram. Run only Telegram tests with:

```bash
pytest -q tests/test_telegram_bot.py
```

Live Groq tests are optional and consume API access:

```bash
pytest -q -m live --override-ini addopts=
```

They require `GROQ_API_KEY` and the sample files under `input/`.

## 4. Run and manually test Telegram

Start the bot with the environment active and all three variables exported:

```bash
python -m crm.telegram_bot
```

Keep the terminal open and laptop awake. Stop the bot with `Ctrl-C`.

From an allowlisted account in a private chat, send one business-card photo (or
JPEG/PNG document) and put only the person's name in its caption. The bot
downloads the image temporarily, runs Groq card extraction through the graph,
and deletes the temporary image after processing.

On successful extraction and schema validation:

```text
✓ Input accepted

Name: Ada Lovelace
Status: complete
```

Useful manual checks:

| Action | Expected result |
|---|---|
| Send `/start` or `/help` privately | Input instructions |
| Send a supported image without a caption | Missing-caption rejection |
| Send text without an image | Supported-format rejection |
| Send a PDF or album | Supported-format rejection |
| Message from an unlisted account | Authorization rejection |
| Use the bot in a group | Private-chat-only rejection |

Telegram currently sends `voice_path=None`; voice files are supported by the
CLI graph, not by a multi-message Telegram conversation.

## 5. Run and manually test the CLI

Card only:

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
```

Card plus optional voice note:

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --voice input/6134386456120009929.ogg
```

The installed `crm` command is equivalent. On success, JSON includes
`contact_evidence`; with voice it also includes `voice_transcript` and copies
that transcript into `conversation_notes`. It exits `0` on completion and `1`
for invalid input or provider errors.

## Current graph

```text
START → load_input → validate_input → extract_card → validate_extraction
  → voice_present?
       /          \
     no            yes
      |      transcribe_voice
      \          /
       merge_context → finalize → END
```

The Telegram adapter handles access control, media download, formatting, and
cleanup. It is not a graph node.

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

The Telegram adapter returns only its user-facing acceptance/rejection message;
it does not print contact evidence to the terminal or save it. Use the CLI when
you need to inspect the complete graph result as JSON.

## Not implemented

- Telegram voice-message conversations
- PostgreSQL/contact persistence
- duplicate detection
- embeddings or RAG
