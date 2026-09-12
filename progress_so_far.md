# Progress So Far — AI Conference CRM

Last updated: 2026-09-12

This document records only work that has been specified and completed. The next task is not listed here because it has not been specified.

Lessons (what to understand): [understandable_so_far.md](understandable_so_far.md).  
How to run the current app: see [how_to_run.md](how_to_run.md).

After every later task that passes verification, update **this file** and `understandable_so_far.md` before stopping.

**Agent tooling in this repo:**

- **Ponytail (full)** — `.cursor/rules/ponytail.mdc`. Smallest working **code**. Learning reports still follow [AGENTS.md](AGENTS.md).
- **Graphify-Labs Graphify** — https://github.com/Graphify-Labs/graphify only. Rule: `.cursor/rules/graphify.mdc`. Query `graphify-out/` first, then teach from what you found using the AGENTS.md formats.

---

## What this project is

A small conference CRM capture workflow. The user provides:

- a person's name
- a business-card image
- an optional voice-file path

The system is built as an explicit LangGraph. Deterministic Python handles validation, matching, persistence, and write verification. Groq is used to read the card image, transcribe an optional voice note, and (after a verified write) embed the search document. Contacts live in local SQLite (`data/crm.db`). Semantic search uses `sqlite-vec`; the vector index only stores IDs, not the canonical row.

No PostgreSQL or Telegram yet.

The full current graph (Tasks 1–8) is in [understandable_so_far.md](understandable_so_far.md). Observability wraps that graph; it does not add nodes. Search is a separate CLI path.

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

**Status:** Done. Independent verifier PASS (`pytest -q` → 30 passed, 2 deselected).

**What we built:** An explicit LangGraph fork after card extraction. Voice is optional conversation context, not identity. Both paths meet at `merge_context`.

**Graph after Task 3** (persist and verify came later):

```text
START → load_input → validate_input → extract_card → validate_extraction
  → voice_present? → (transcribe_voice or skip) → merge_context → finalize
```

The fork is a real `add_conditional_edges` call in `crm/graph.py`, not a hidden `if` inside one node.

**Optional behaviour:**

- Name + image only: skip `transcribe_voice`, leave voice fields `None`, still `complete`. Groq Whisper is not called.
- Name + image + existing `.ogg`: run `transcribe_voice`, store the text, still `complete`.
- Voice supplied but STT fails: `status="error"` (not silently ignored).

**New state fields (`crm/state.py`):**

- `voice_transcript` — raw Whisper text, or `None`
- `conversation_notes` — same text attached as context in `merge_context`, or `None`

**Provider isolation:**

```text
LangGraph transcribe_voice  →  VoiceTranscriber.transcribe(path)  →  Groq Whisper
                                         ↑
                                tests: FakeTranscriber
```

Live impl: official Groq client, `GROQ_API_KEY`, model `whisper-large-v3`. Original `.ogg` (Opus) is passed through. No FFmpeg. Groq accepts `ogg` directly.

**Boundary:**

```text
business card → ContactEvidence (identity)
voice note    → conversation_notes (context)
```

Voice never overwrites `company`, email, or other card fields.

**CLI:**

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
python -m crm --name "Sarah Khan" --image input/visiting_card.png --voice input/6134386456120009929.ogg
```

Telegram is not part of this task. The CLI still takes a local voice-file path.

**Key files:** `crm/graph.py`, `crm/state.py`, `crm/providers/base.py`, `crm/providers/groq.py`, `tests/test_voice.py`, `tests/test_live_transcribe.py`

---

## Live checks

On branch `ft/Core_Engine`, with `GROQ_API_KEY` in `.env`.

**Card only:**

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png
```

Result: `status="complete"`. `contact_evidence` included Sarah Khan, NexaTech Solutions, Product Manager, email, phone, website, and address. `voice_transcript` and `conversation_notes` were `None`.

**Card + sample voice** (`input/6134386456120009929.ogg`):

```bash
python -m crm \
  --name "Sarah Khan" \
  --image input/visiting_card.png \
  --voice input/6134386456120009929.ogg
```

Result: `status="complete"`. Card fields unchanged. Voice context:

> So I met this person in an event. She is a very good contact for our CRM project and would like to follow up with her after two weeks.

---

## Tests

Default (no live API):

```bash
pytest -q
```

Last recorded default run after the Discord name-from-card + embed fallback fix: **101 passed, 2 deselected**.

Optional live smoke tests (need `GROQ_API_KEY`; card image and/or `input/6134386456120009929.ogg`):

```bash
pytest -q -m live --override-ini addopts=
```

---

## Task 4 — SQLite CRM Persistence, Matching, and Notes

**Status:** Done. Independent verifier PASS (`pytest -q` → 46 passed, 2 deselected).

**What we built:** After merge, normalize and search SQLite. Explicit CREATE vs UPDATE. Notes append. LLM does not match people.

**Graph after Task 4** (verify_write came next):

```text
merge_context
      ↓
persistable?
   /         \
finalize   normalize_contact
                  ↓
             search_crm
                  ↓
            match_found?
             /         \
     update_contact  create_contact
             \         /
              finalize → END
```

**Store:** `crm/db.py` (`sqlite3`, default `data/crm.db`). Tests use a temp file.

**Match order:** normalized email, then phone, then full_name + company.

**Notes:** CREATE may have `NULL`. UPDATE appends with a blank line. No new notes → leave old notes. Null fields do not erase stored values.

**Key files:** `crm/db.py`, `crm/normalize.py`, `crm/graph.py`, `tests/test_crm.py`

---

## Write verification

**Status:** Done. Independent verifier PASS (`pytest -q` → 55 passed, 2 deselected).

**What we built:** After CREATE/UPDATE the graph re-reads the row. `complete` requires `verified_contact` from that read, not from the write return value.

```text
create_contact ↘
                verify_write → write_ok? → finalize → END
update_contact ↗
```

Read-back is `ContactStore.get` (SQLite). PostgreSQL was not added.

**Key files:** `crm/graph.py`, `tests/test_verify.py`

---

## Task 6 — Semantic Contact Retrieval with sqlite-vec

**Status:** Done. Independent verifier PASS (`pytest -q` → 65 passed, 2 deselected).

**What we built:** After a verified write, build a short search document, embed it, and store the vector in `sqlite-vec`. `crm query` finds contacts by meaning, then loads the SQLite rows.

**Graph after a successful write:**

```text
verify_write → write_ok?
   fail → finalize
   ok   → build_search_document → create_embedding → store_embedding → finalize
```

Failed verify skips the embed path. Embed or store failure keeps `status="error"` (not `complete`).

**Storage:** `contacts` table unchanged. Separate virtual table `contact_embeddings` (`vec0`). `rowid` = `contact_id`. Upsert is DELETE then INSERT so updates do not leave a stale vector.

**Search document:** non-blank `full_name`, `company`, `job_title`, `notes` only.

**Provider isolation:**

```text
LangGraph create_embedding  →  EmbeddingProvider.embed(text)  →  Groq
                                         ↑
                                tests: FakeEmbedder
```

Live: `GroqEmbedder` tries Groq nomic slugs (`nomic-embed-text-v1_5`, then `nomic-embed-text-v1.5`, dim 768), `GROQ_API_KEY`. If Groq returns `model_not_found`, it falls back to a local 768-d token-hash vector so capture can still complete. Default tests inject `FakeEmbedder` (dim 8). No key, no network.

**CLI:**

```bash
python -m crm query "Who did I meet regarding AI workflow automation?"
```

Embeds the question, KNN on `contact_embeddings`, loads contacts by id. JSON list with `distance`. Default `--limit` 5.

This Mac’s CPython cannot load SQLite extensions, so `crm/db.py` uses a thin APSW wrapper so `sqlite_vec.load` still works.

**Key files:** `crm/search.py`, `crm/providers/embeddings.py`, `crm/db.py`, `crm/graph.py`, `crm/cli.py`, `tests/test_embeddings.py`

---

## Task 7 — LangSmith Observability and Evaluation

**Status:** Done. Independent verifier PASS (`pytest -q` → 83 passed, 2 deselected).

**What we built:** Optional LangSmith tracing on live model calls. An offline dataset of 10 capture cases. Five deterministic evaluators. `python -m crm.eval` runs the real graph (fakes + temp SQLite) through `langsmith.evaluate` and writes scores.

**Graph change:** none.

**Tracing:** `crm/tracing.py` `enable_tracing()`. If `LANGSMITH_API_KEY` is set: `LANGSMITH_TRACING=true`, project `ai-conference-crm`. No key → no-op. Live Groq `extract_card` / `transcribe` / `embed` are `@traceable`. CLI calls `enable_tracing()` after `load_dotenv`.

**Dataset** (`eval/dataset.json`): complete-card, partial-card, missing-phone, missing-email, existing-contact, new-contact, voice-present, voice-absent, conflicting-voice, unsupported-fields.

**Evaluators** (code, not LLM judges): extraction correctness; unsupported-field hallucination; CREATE vs UPDATE; duplicate avoidance; post-write verification.

**Experiment:** `eval/latest_experiment.json`. All means 1.0 with fakes. `experiment_url` is null (no LangSmith key). Weakest/hardest labeled case: `conflicting-voice`.

**CLI:**

```bash
python -m crm.eval
```

Default pytest does not upload and does not need a LangSmith key.

**Key files:** `crm/eval.py`, `crm/tracing.py`, `eval/dataset.json`, `eval/latest_experiment.json`, `tests/test_eval.py`

---

## Task 8 — Text Notes and Semantic Search Interface

**Status:** Done. Independent verifier PASS (`pytest -q` → 93 passed, 2 deselected).

**What we built:** Optional `--notes` on capture. Typed and voice context merge in ordinary Python. `crm query` prints a short ranked list from SQLite rows. Search does not run the capture graph.

**Graph:** same nodes. `load_input` now copies `typed_notes`. `merge_context` joins typed and/or voice (`"\n\n"` when both). No notes AI node.

**CLI:**

```bash
python -m crm --name "Sarah Khan" --image input/visiting_card.png --notes "Potential consulting lead."
python -m crm query "Who did I speak with about data warehouse consulting?"
```

`--notes` and `--voice` are both optional. Query default `--limit` 5. Results are name, company, title, notes from `contacts`.

**Key files:** `crm/graph.py` (`merge_context`), `crm/cli.py`, `crm/state.py`, `crm/search.py`, `tests/test_voice.py`, `tests/test_crm.py`, `tests/test_cli.py`

---

## Discord DM adapter

**Status:** Done. Independent verifier PASS (`pytest -q` → 101 passed, 2 deselected). Follow-up fix: name comes from the card; Groq embed 404 no longer fails the run.

**What we built:** A Discord DM adapter. Image + optional notes wait in memory. The bot does not ask for a name. Follow-up voice or `save` runs the existing capture graph with `name=None`; `validate_extraction` copies `full_name` from the card. `/query` searches and does not write.

**Graph change:** none.

**CLI:**

```bash
python -m crm.discord_bot
```

Needs `DISCORD_BOT_TOKEN` and Message Content Intent. DMs only.

**Key files:** `crm/discord_bot.py`, `tests/test_discord.py`, `how_to_run.md`

---

## What is intentionally not built yet

These were not specified as later work:

- PostgreSQL / SQLAlchemy / migrations
- pgvector / RAG chat
- Telegram, Slack, or WhatsApp
- Structured reminders / follow-up extraction from the transcript
- A live-vision LangSmith experiment (this task’s experiment uses fakes so it stays offline)

---

## Where to look

| Topic | File |
| --- | --- |
| Graph nodes and edges | `crm/graph.py` |
| Shared graph state | `crm/state.py` |
| Contact schema | `crm/schemas.py` |
| SQLite store | `crm/db.py` |
| Vector index | `crm/db.py` (`contact_embeddings`), `crm/search.py` |
| Write verification | `crm/graph.py` (`verify_write`), `tests/test_verify.py` |
| Normalization | `crm/normalize.py` |
| Groq vision + Whisper | `crm/providers/groq.py` |
| Groq embeddings | `crm/providers/embeddings.py` |
| Provider interfaces | `crm/providers/base.py` |
| CLI (capture + query) | `crm/cli.py` |
| Discord DM adapter | `crm/discord_bot.py` |
| Tracing | `crm/tracing.py` |
| Eval dataset + experiment | `eval/dataset.json`, `crm/eval.py`, `eval/latest_experiment.json` |
| Sample card | `input/visiting_card.png` |
| Sample voice | `input/6134386456120009929.ogg` |
| How to run | `how_to_run.md` |
| What to understand | `understandable_so_far.md` |
| Learning harness | `AGENTS.md` |
| Ponytail rule | `.cursor/rules/ponytail.mdc` |
| Graphify rule | `.cursor/rules/graphify.mdc` |
| Code knowledge graph | `graphify-out/graph.json` |
