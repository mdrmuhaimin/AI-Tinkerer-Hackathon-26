# Discord DM adapter — plan for a later build

Saved from the Task 9 planning session. Do not implement until the human asks.

Branch when building: `ft/discord` (from current `main`).

Discord is another **input/output panel**. It does not join LangGraph. The CLI stays as-is. Same rule as [telegram_plan.md](telegram_plan.md): the bot maps a conversation to `{name, image_path, voice_path, typed_notes}` or to `query_contacts`, then replies.

**Surface:** DMs only. Session key is the Discord user id.

```text
Discord DM
     ↓
discord_bot adapter
     ├─ image + name + notes → pending intake
     ├─ follow-up voice or "save" → existing capture graph
     └─ /query → query_contacts
              ↓
     contacts + sqlite-vec
              ↓
     Discord reply
```

## User flow

**Capture (two turns, voice optional)**

1. User DMs a **business-card image**. Message text: first line is the **name** (required by `validate_input` in `crm/graph.py`); any following lines are **typed notes**.
2. Bot downloads the image to a temp file, stores a pending intake for that user, replies: card received; send a voice message or type `save`.
3. Follow-up **voice message** or audio attachment (`audio/ogg` / `voice-message.ogg` or other `audio/*`) → set `voice_path`, invoke `build_graph()`, reply with a short result (name, company, `crm_action`, `contact_id`, notes), clear pending.
4. Follow-up `save` / `done` → same invoke **without** voice.
5. Extra typed text while pending **appends** to `typed_notes` (deterministic `"\n\n"`, no LLM).

If the first DM already has **image + voice**, skip pending and run the graph immediately.

If the image has **no name**, bot asks for the name and does not run the graph yet.

Native Discord voice messages are OGG/Opus (same family as Telegram). Pass the original file to Whisper; no FFmpeg for that path.

**Search (never capture)**

- Slash command: `/query Who did I meet regarding data warehouse consulting?`
- Reuse `crm/search.py` `query_contacts` and `_format_query_hits` in `crm/cli.py`.
- Do **not** call `build_graph`. Do **not** create/update contacts.

## Out of scope

- New graph nodes
- Using vectors for duplicate matching
- Telegram, Slack, WhatsApp, RAG answers, web UI
- Persisting pending intake across bot restarts

## Implementation (when we build)

**Run:** `python -m crm.discord_bot`

**Token:** `DISCORD_BOT_TOKEN` in `.env` (gitignored). Gateway connection — no public URL.

**Library:** `discord.py` (intents: DMs + `message_content`; enable Message Content Intent in the Discord Developer Portal).

**New module:** `crm/discord_bot.py` — parse DM, download attachments, pending dict, call graph/query, reply.

**Pending store:** in-memory `dict[user_id, Pending]`. Lost on restart.

Live bot uses the same `GROQ_API_KEY` + `data/crm.db` as the CLI.

## Tests (when we build)

`tests/test_discord.py` with fake messages/attachments and injected fake graph/store/embedder. Default suite: no Discord API, no network.

- Image + name (+ optional notes) creates pending and does not persist yet.
- Follow-up voice runs the real `build_graph` with fakes and persists notes + transcript.
- `save` without voice completes capture; transcriber is not called.
- `/query` ranks a relevant contact and never calls `build_graph`.
- Guild/channel messages are ignored.
- Existing CLI / graph tests still pass.

## Docs (when we build)

`how_to_run.md`: bot command, portal intents, DM examples, `DISCORD_BOT_TOKEN`.

After PASS: update `progress_so_far.md` and `understandable_so_far.md`.

## Process when building

Learning harness: Learning Step → implementer (TDD, Ponytail) → independent verifier → checkpoint. Work stays on `ft/discord`.
