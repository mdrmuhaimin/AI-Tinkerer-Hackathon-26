# What You Should Understand So Far

Last updated: 2026-09-12

This is the learning notebook for the AI Conference CRM. It is the accumulated **What You Should Understand Now** after each completed task.

What was built (files, tests, CLI): [progress_so_far.md](progress_so_far.md).  
How to run: [how_to_run.md](how_to_run.md).

After every later task that passes verification, the orchestrator must update **this file** and `progress_so_far.md` before stopping.

---

## The split that runs through everything

| Kind | Examples | Who does it |
| --- | --- | --- |
| Probabilistic | Read a card image, transcribe voice, turn text into an embedding | Groq, behind a small interface |
| Deterministic | Validate paths, normalize, match, CREATE/UPDATE, verify the row, KNN lookup, load rows by id | Python + SQLite + sqlite-vec |

Do not ask a model to decide something ordinary code can decide.

---

## Task 1 — LangGraph is state + nodes + edges

LangGraph is not “an agent.” It is a **state object**, named functions, and explicit edges.

If you want to know what the system knows, open `crm/state.py`, not a prompt.

Validation is ordinary Python. An image is required. A typed name is required only when there is no image. With a card image, blank name is fine: `validate_extraction` copies `full_name` from the card. The run still reaches END so you can inspect the result.

**Check:** Why can `finalize` stay on the linear path when input is invalid?

---

## Task 2 — The model does not own the result

The vision model returns a dict. `ContactEvidence.model_validate` decides if that dict is usable.

The graph talks only to `CardExtractor.extract_card(path)`. Groq lives in the provider. Tests inject `FakeExtractor`.

Failure is a state: missing env or a dead API → `error`. Bad JSON → `invalid`.

**Check:** If `validate_input` already set `invalid`, what actually prevents the API call?

---

## Task 3 — Voice is optional context, not identity

A missing `--voice` is a **route**, not an error. `voice_present` skips `transcribe_voice`. Whisper is not called. Notes stay `None`.

Both paths meet at `merge_context`.

```text
business card → ContactEvidence (who)
voice note    → conversation_notes (what we discussed)
```

Voice never overwrites company, email, or other card fields.

**Check:** After `validate_extraction` with no `--voice`, which nodes run, and is Whisper called?

---

## Task 4 — Persistence, keys, and notes

A successful capture is a **row** in SQLite (`data/crm.db`), not only JSON.

Normalize before search: email lowercased, phone as digits, name/company stripped and casefolded.

Match in this order, first hit wins:

1. normalized email
2. else normalized phone
3. else normalized name **and** company

Name alone is not a key. Two Sarahs with `sarah@nexatech.com` and `sarah@other.com` are two people. Same name, different company, no email/phone → two rows.

CREATE vs UPDATE is an explicit graph fork (`match_found`). Failed UPDATE does not CREATE.

Notes append (`old` + blank line + `new`). No new notes → leave old notes. A new `null` field does not erase a stored value.

The LLM does not detect duplicates.

**Check:** Why match on email (or name+company) instead of “they sound like the same person”?

---

## Write verification — proof vs hope

`create()` returning an id is a claim. `store.get(id)` is evidence.

`verify_write` re-reads the row and compares intended non-empty fields. Missing row, wrong values, or a get exception → `error`.

`finalize` sets `complete` only when `contact_id` **and** `verified_contact` are present.

The read goes through `ContactStore` (SQLite today). The graph does not need to know the engine.

**Check:** If create returns `contact_id=7` but `get(7)` is missing, what is `status`? Is the CLI allowed to print `complete`?

---

## Task 6 — The vector is an index, not the record

An embedding is a list of numbers that represents the *meaning* of a short document. Nearby vectors mean similar meaning. The CRM still stores the person in `contacts`. `contact_embeddings` only answers: “which `contact_id`s are closest to this question?”

The searchable document is not the whole row. It is `full_name`, `company`, `job_title`, and `notes`. Email and phone help *find the same person later*. They do not help *“who talked about automation?”*

This is a different job from duplicate matching:

| Job | Tool | Example |
| --- | --- | --- |
| Same person? | Deterministic keys | same email → UPDATE |
| Related conversation? | Vector similarity | “workflow automation” → Sarah’s notes |

The embed path runs only after `write_ok`. A failed verify must not write a vector for a row you do not trust. When notes change, DELETE + INSERT replaces that `contact_id`’s vector so search does not keep the old meaning.

The graph calls `EmbeddingProvider.embed(text)`. Groq HTTP stays in the provider. Tests inject `FakeEmbedder`. If this Groq account has no embedding model, the provider logs a warning and returns a local token-hash vector (same 768 dimensions) so the contact write is not rolled back for a search-index miss.

`crm query` is not a capture-graph node. It embeds the question, asks sqlite-vec for IDs, then `ContactStore.get`.

**Check:** After a notes update, why must the old vector be replaced — and why is that not the same as changing the `contacts` row?

---

## Task 7 — A trace is not a score

Tracing answers “what ran?” Evaluation answers “was it right?”

LangSmith traces (when `LANGSMITH_API_KEY` is set) wrap live Groq extract / transcribe / embed under the graph invoke. They do not add CRM nodes.

The experiment is a **labeled dataset** plus **code evaluators**. Each example has expected `contact_evidence`, `crm_action`, `null_fields`, and `verified`. The target is the real capture graph. Fakes stand in for Groq so default eval needs no key.

All five scores being 1.0 is honest, not success theater: the fake extractor returns the labeled card. The graph’s job is matching, CREATE vs UPDATE, verify, and “voice does not overwrite identity.” That path is deterministic.

The hardest labeled case is still `conflicting-voice`. The voice says she works at Google. The card says Analytical Engines. A live model (or a sloppy merge) could copy the voice onto the card. Our graph must keep card identity and put the voice in notes.

**Check:** If traces appear in LangSmith but `unsupported-fields` invents an email, did evaluation pass? Which evaluator should fail?

---

## Task 8 — Two inputs, one merge; two jobs, two paths

Typed notes and a voice transcript are two sources of the same kind of thing: conversation context. They enter state separately (`typed_notes`, `voice_transcript`). `merge_context` joins them with a blank line. No model rewrites that.

Absence of `--notes` or `--voice` is normal. Text-only never calls Whisper. Voice-only never needs typed text.

Search is a different path:

```text
question → query embedding → sqlite-vec IDs → contacts row → print
```

The question gets a new embedding at query time. That is not the contact’s stored vector. The stored vector was built from the search document after a verified write. Results are CRM rows, not vec-table metadata.

**Check:** You type `--notes` and also pass `--voice`. Which node combines them, and does `crm query` run that node?

---

## Discord — another door, same rooms

The bot does not sit on the graph. A DM is translated into the same payload the CLI builds, or into `query_contacts`.

Pending intake is a dict keyed by Discord user id. The card waits. Voice or `save` is when `build_graph()` runs. Typed DM text is notes, not the contact name. `/query` never does that.

Guild messages are ignored. DMs only.

**Check:** You send a card image in a Discord DM, then `/query who did I meet?` before `save`. Did a contact get written?

---

## Current graph (all tasks)

```text
START
  ↓
load_input (name, image, optional voice, optional typed_notes)
  → validate_input → extract_card → validate_extraction
  ↓
voice_present?
   /        \
 no          yes → transcribe_voice
  \          /
   merge_context   ← typed and/or voice, no LLM
        ↓
   persistable?
      /      \
 finalize  normalize_contact → search_crm → match_found?
                                    /              \
                          update_contact      create_contact
                                    \              /
                                     verify_write
                                          ↓
                                      write_ok?
                                       /        \
                                 fail            ok
                                  |               |
                                  |    build_search_document
                                  |         ↓
                                  |    create_embedding
                                  |         ↓
                                  |    store_embedding
                                   \        /
                                    finalize → END
```

---

## Tooling (how we work, not what the CRM is)

- **Ponytail:** smallest **code**. Does not skip teaching.
- **Graphify-Labs Graphify** (https://github.com/Graphify-Labs/graphify): query `graphify-out/` before exploring files, then teach from what you found.

Required reports after every specified task: Learning Step → Implementation Update → Evaluation → What You Should Understand Now. Then update this file and `progress_so_far.md`.
