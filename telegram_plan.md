The cleanest integration is to keep Telegram completely outside LangGraph. Your existing graph remains the application; Telegram simply becomes another way of constructing its input.

```text
Telegram
   ↓
Telegram Input Adapter
   ↓
{name, image_path, voice_path}
   ↓
Existing LangGraph
START → load_input → validate_input → finalize → END
   ↓
Telegram Response
```

For local development, use **long polling**, not webhooks. Telegram supports long polling through `getUpdates`, so the bot can run entirely on your laptop without exposing a public HTTP endpoint. Webhooks and long polling are mutually exclusive. ([Telegram Core][1])

I would implement it in two stages:

1. **Telegram MVP.** Add `python-telegram-bot`. Store `TELEGRAM_BOT_TOKEN` in `.env`. Run a separate command such as `python -m crm.telegram_bot`. Keep the existing CLI untouched.

2. **Define the simplest input contract.** For now, the user sends a business-card photo and puts the person's name in the photo caption:

```text
[Business card photo]

Ada Lovelace
```

The bot downloads the image to a temporary local file and invokes your existing graph with:

```python
{
    "name": "Ada Lovelace",
    "image_path": "/tmp/...",
    "voice_path": None
}
```

3. **Return the graph result through Telegram.** Initially the reply can be deliberately boring:

```text
✓ Input accepted

Name: Ada Lovelace
Status: complete
```

If validation fails:

```text
✗ Input rejected

name is required
```

4. **Keep Telegram logic isolated.** I would add roughly:

```text
crm/
├── graph.py              ← existing LangGraph
├── cli.py                ← existing CLI adapter
└── telegram_bot.py       ← new Telegram adapter
```

Both CLI and Telegram call the **same graph**. Neither contains CRM business logic.

5. **Test without Telegram's real servers.** Mock the Telegram message/file objects and verify that a photo + caption becomes the correct graph input. Also verify missing caption, failed download, invalid image and graph validation errors. The existing eight graph tests must continue passing.

6. **Evaluation for this task.** The verifier should prove that sending a photo with a name reaches the existing LangGraph, the downloaded file really exists when the graph validates it, the result comes back to Telegram, the CLI still works, and no Telegram-specific logic has leaked into graph nodes.

7. **Add voice only after the basic adapter works.** At that point the Telegram interaction becomes:

```text
User: [card photo] + "Ada Lovelace"

Bot: Card received.
     Send a voice note, or /done.

User: [voice note]

Bot: Processing...
```

That requires a tiny per-chat **pending intake state**, so I would deliberately keep it out of the first Telegram task.

`python-telegram-bot` already provides `run_polling()` to initialize the application, poll Telegram and shut down cleanly, which fits your laptop-based hackathon setup well. ([Python Telegram Bot][2])

So the learning objective for this task is important: **LangGraph is your application workflow; Telegram and CLI are interchangeable interfaces into that workflow.** Don't make Telegram a LangGraph node.

[1]: https://core.telegram.org/bots/api?utm_source=chatgpt.com "Telegram Bot API"
[2]: https://docs.python-telegram-bot.org/_/downloads/en/v22.1/pdf/?utm_source=chatgpt.com "python-telegram-bot Documentation"
