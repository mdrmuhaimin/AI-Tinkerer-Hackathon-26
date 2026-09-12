# How to Run and Test the AI Conference CRM

This guide covers the current local interfaces:

- the Telegram input adapter, which runs on your laptop using long polling; and
- the original command-line interface (CLI), which invokes the same LangGraph.

The current graph validates inputs only. It does not yet read a business card or save a contact.

## Prerequisites

- Python 3.11 or newer
- A terminal (the commands below use macOS/Linux `zsh` syntax)
- A Telegram account
- A Telegram bot token obtained by creating a bot through the official [@BotFather](https://t.me/BotFather) account
- Your own numeric Telegram user ID, obtained through a trusted method

Never put a real bot token or user ID in source code, documentation, screenshots, commits, or messages to other people. The examples below use deliberately fake placeholders.

## 1. Set up the project

Run these commands from the repository root:

```bash
cd /Users/apple/Documents/projects/AI-Tinkerer-Hackathon-26
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install -e ".[dev]"
```

Both version commands should report Python 3.11 or newer. Activating `.venv` keeps this project's packages separate from system Python. The editable install includes LangGraph, `python-telegram-bot`, and the `pytest` development dependency.

When returning to the project in a new terminal, activate the environment again:

```bash
cd /Users/apple/Documents/projects/AI-Tinkerer-Hackathon-26
source .venv/bin/activate
```

## 2. Run automated tests

Run the complete test suite:

```bash
pytest -q
```

The exact number of passing tests may grow as the project evolves. The important result is that the command ends with no failures or errors.

Run only the Telegram adapter tests:

```bash
pytest -q tests/test_telegram_bot.py
```

These tests use fake Telegram updates and files; they do not contact Telegram or require a real bot token.

## 3. Configure Telegram

In the same terminal that will run the bot, export both required variables:

```bash
export TELEGRAM_BOT_TOKEN="123456789:FAKE_REPLACE_WITH_YOUR_BOT_TOKEN"
export TELEGRAM_ALLOWED_USER_IDS="111111111"
```

Replace both fake values with your real values locally. To allow more than one private Telegram account, use comma-separated numeric IDs:

```bash
export TELEGRAM_ALLOWED_USER_IDS="111111111,222222222"
```

This variable is a private-chat allowlist. A message must come from one of those numeric user IDs and from a private chat. Group and channel use is not supported.

The application does not automatically load a `.env` file, so exporting the variables in the active shell is the clearest supported setup. Do not commit secrets to the repository.

### Find your numeric Telegram user ID

One simple option is to message the commonly used [@userinfobot](https://t.me/userinfobot) and copy the numeric user ID it returns. This is a third-party bot: it receives the message and basic Telegram account information you share with it. Verify the username before using it, and do not send it your CRM bot token or any private content.

If you do not want to use a third-party bot, use Telegram's official Bot API `getUpdates` method after sending a private message to your newly created bot, and read `message.from.id` from the response. Take care not to put the token in shell history, screenshots, logs, or shared URLs. This project does not provide a `/myid` command.

## 4. Start and stop the Telegram bot

Start the bot from the repository root with the virtual environment active:

```bash
python -m crm.telegram_bot
```

The process stays running and receives updates from Telegram through long polling. Keep the terminal open, keep the laptop awake and connected to the internet, and leave the process running while using the bot. No webhook, public server, Docker container, or cloud deployment is required.

Stop it with `Ctrl-C`. The bot cannot respond while the process is stopped, the laptop is asleep, or the laptop has no network connection.

## 5. Manually test the Telegram bot

Use an allowlisted Telegram account in a private chat with the bot. Use a fake or non-sensitive sample business-card image while testing.

### Happy path: Telegram photo

1. Send one image using Telegram's normal photo option.
2. Put only `Ada Lovelace` in the image caption.
3. Send the message.

Expected reply, exactly:

```text
✓ Input accepted

Name: Ada Lovelace
Status: complete
```

### Happy path: image document

1. Send one JPEG or PNG using Telegram's file/document option.
2. Put only `Ada Lovelace` in the document caption.
3. Send the message.

Expected reply, exactly:

```text
✓ Input accepted

Name: Ada Lovelace
Status: complete
```

### Rejection and access checks

| Check | Action | Expected reply or behavior |
|---|---|---|
| `/start` | Send `/start` from an allowlisted private account. | Instructions say to send one business-card photo or JPEG/PNG document and use only the person's name as its caption. |
| `/help` | Send `/help` from an allowlisted private account. | The same usage instructions appear. |
| Missing caption | Send a photo or supported image document without a caption. | `✗ Input rejected`, followed by `Add the person's name as the image caption and send it again.` |
| Text only | Send `Ada Lovelace` as an ordinary text message. | `✗ Input rejected`, followed by the accepted photo/document format. |
| Unsupported document | Send a PDF or another non-JPEG/PNG document with a caption. | `✗ Input rejected`, followed by the accepted photo/document format. |
| Album | Select and send multiple photos as one Telegram album. | The album items are rejected with the accepted single-image format; no intake is processed. |
| Group chat | Add the bot to a group and send `/start@YourBotUsername`, replacing the placeholder with its username. | If Telegram delivers the command, the bot replies `This bot only works in private chats.` Ordinary group messages may not be delivered while BotFather privacy mode is enabled. |
| Unauthorized account | From a different account whose numeric ID is not in the allowlist, message the bot privately. | `You are not authorized to use this bot.` |

Do not deliberately corrupt credentials, intercept requests, or expose the token to simulate internal or download failures. Automated tests safely cover download and graph failure paths.

## What `Status: complete` means

`Status: complete` means only that the existing deterministic graph accepted the name and temporary image-file inputs. It does **not** mean that the card was read or that a contact was saved.

The current MVP has no:

- OCR or business-card field extraction
- voice-note flow or transcription
- database save
- duplicate detection
- persistent image/contact storage
- RAG or semantic retrieval

The downloaded Telegram image is temporary and is removed after the graph runs.

## Run the CLI manually

The CLI remains available and uses the existing graph directly. The image path must point to an existing file:

```bash
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg
```

The graph also still accepts an optional existing voice-file path through the CLI, although Telegram has no voice workflow:

```bash
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg --voice /path/to/note.wav
```

After the editable install, the equivalent console command is:

```bash
crm --name "Ada Lovelace" --image /path/to/card.jpg
```

For a quick validation-only CLI test, an ordinary placeholder file is sufficient because the current graph checks file existence rather than image contents:

```bash
echo "placeholder" > /tmp/card.jpg
python -m crm --name "Ada Lovelace" --image /tmp/card.jpg
```

On success, the CLI prints the final graph state as JSON and exits with code `0`:

```json
{
  "name": "Ada Lovelace",
  "image_path": "/tmp/card.jpg",
  "voice_path": null,
  "status": "complete",
  "errors": []
}
```

On validation failure, it prints an invalid state and exits with code `1`. For example, a blank name produces `name is required` in `errors`.

```bash
python -m crm --name "" --image /tmp/card.jpg
echo $?
```

## Current graph flow

```text
START → load_input → validate_input → finalize → END
```

The Telegram adapter handles access control, supported media, download, response formatting, and temporary-file cleanup. It then maps an accepted message to the same graph input used by the CLI. Telegram is not a graph node.

## Troubleshooting

### `TELEGRAM_BOT_TOKEN is required`

The variable is missing or blank in the terminal running the bot. Export it in that terminal, then run the bot again:

```bash
export TELEGRAM_BOT_TOKEN="123456789:FAKE_REPLACE_WITH_YOUR_BOT_TOKEN"
```

### `TELEGRAM_ALLOWED_USER_IDS is required`

Export at least one numeric Telegram user ID in the same terminal:

```bash
export TELEGRAM_ALLOWED_USER_IDS="111111111"
```

### `TELEGRAM_ALLOWED_USER_IDS must contain numeric IDs`

Remove usernames, `@` signs, spaces used as separators, and other text. Supply numeric IDs separated by commas, for example `111111111,222222222`.

### `You are not authorized to use this bot.`

The sending account's numeric user ID does not match the allowlist. Verify the ID through a trusted method, correct `TELEGRAM_ALLOWED_USER_IDS`, stop the running process, and restart it so configuration is reloaded. The bot does not implement a `/myid` command.

### The bot does not respond

Check that:

- `python -m crm.telegram_bot` is still running without a startup error;
- the virtual environment is active and dependencies are installed;
- the laptop is awake and online;
- you opened the correct bot and sent it a message; and
- no other process is polling the same bot token.

This implementation uses polling, not webhooks. Its polling startup normally clears an existing webhook automatically. Another active polling process using the same token can still cause a conflict, so stop the other process and retry. Only investigate webhook configuration separately if Telegram reports an actual webhook-related error. Do not paste the token into logs, issue reports, screenshots, or chat messages while diagnosing it.

### Import, dependency, or Python-version errors

Confirm the active interpreter and reinstall the package:

```bash
source .venv/bin/activate
python --version
python -m pip install -e ".[dev]"
```

Python must be 3.11 or newer. If `.venv` was created with an older Python, create a new environment using an installed Python 3.11+ interpreter.

### A bot token may have been exposed

Treat it as compromised. Revoke/regenerate it through the official @BotFather, replace the exported value, and restart the bot. Do not commit the replacement.

### CLI reports `image file not found`

Use an absolute path or a path relative to the directory where the command runs, and confirm that it points to a file:

```bash
ls -l /path/to/card.jpg
```
