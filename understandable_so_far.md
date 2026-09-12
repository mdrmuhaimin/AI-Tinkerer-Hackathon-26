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
| Probabilistic | Read a card image, transcribe voice, phrase a grounded search answer | Groq, behind a small interface |
| Deterministic | Validate paths, normalize, match, CREATE/UPDATE, verify the row, FTS retrieval | Python + SQLite FTS5 |

Do not ask a model to decide something ordinary code can decide.

---

## Task 1 — LangGraph is state + nodes + edges

LangGraph is not “an agent.” It is a **state object**, named functions, and explicit edges.

If you want to know what the system knows, open `crm/state.py`, not a prompt.

Validation is ordinary Python. Missing name or image is `status="invalid"`. The run still reaches END so you can inspect the result.

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

> **Historical experiment, superseded for default runtime:** the vector code is
> retained only for explicitly injected embedding providers and tests. The live
> Groq embedding assumption was incorrect. Default capture bypasses embedding
> nodes, and current search uses deterministic SQLite FTS5.

An embedding is a list of numbers that represents the *meaning* of a short document. Nearby vectors mean similar meaning. The CRM still stores the person in `contacts`. `contact_embeddings` only answers: “which `contact_id`s are closest to this question?”

The searchable document is not the whole row. It is `full_name`, `company`, `job_title`, and `notes`. Email and phone help *find the same person later*. They do not help *“who talked about automation?”*

This is a different job from duplicate matching:

| Job | Tool | Example |
| --- | --- | --- |
| Same person? | Deterministic keys | same email → UPDATE |
| Related conversation? | Vector similarity | “workflow automation” → Sarah’s notes |

The embed path runs only after `write_ok`. A failed verify must not write a vector for a row you do not trust. When notes change, DELETE + INSERT replaces that `contact_id`’s vector so search does not keep the old meaning.

The experimental graph path calls `EmbeddingProvider.embed(text)` only when a
caller explicitly injects one. Tests inject `FakeEmbedder`; normal runtime does
not construct `GroqEmbedder`.

`crm query` is not a capture-graph node. It embeds the question, asks sqlite-vec for IDs, then `ContactStore.get`.

**Check:** After a notes update, why must the old vector be replaced — and why is that not the same as changing the `contacts` row?

---

## Task 7 — A trace is not a score

Tracing answers “what ran?” Evaluation answers “was it right?”

LangSmith traces (when `LANGSMITH_API_KEY` is set) wrap live Groq extract and
transcribe calls. An embed trace applies only to the retained experimental
injected-provider path. Tracing does not add CRM nodes.

The experiment is a **labeled dataset** plus **code evaluators**. Each example has expected `contact_evidence`, `crm_action`, `null_fields`, and `verified`. The target is the real capture graph. Fakes stand in for Groq so default eval needs no key.

All five scores being 1.0 is honest, not success theater: the fake extractor returns the labeled card. The graph’s job is matching, CREATE vs UPDATE, verify, and “voice does not overwrite identity.” That path is deterministic.

The hardest labeled case is still `conflicting-voice`. The voice says she works at Google. The card says Analytical Engines. A live model (or a sloppy merge) could copy the voice onto the card. Our graph must keep card identity and put the voice in notes.

**Check:** If traces appear in LangSmith but `unsupported-fields` invents an email, did evaluation pass? Which evaluator should fail?

---

## Task 8 — Two inputs, one merge; two jobs, two paths

Typed notes and a voice transcript are two sources of the same kind of thing: conversation context. They enter state separately (`typed_notes`, `voice_transcript`). `merge_context` joins them with a blank line. No model rewrites that.

Absence of `--notes` or `--voice` is normal. Text-only never calls Whisper. Voice-only never needs typed text.

The following was the Task 8 experimental search path and is no longer the default:

```text
question → query embedding → sqlite-vec IDs → contacts row → print
```

The question gets a new embedding at query time. That is not the contact’s stored vector. The stored vector was built from the search document after a verified write. Results are CRM rows, not vec-table metadata.

**Check:** You type `--notes` and also pass `--voice`. Which node combines them, and does `crm query` run that node?

---

## Task 9 — One database, deterministic retrieval, grounded wording

Telegram is an adapter around the same capture graph. It downloads temporary
media, supplies the optional caption as a name hint, waits for voice or `/done`,
formats the result for the chat, and deletes the media. It does not save a second
copy of the contact.

`ContactStore` is the single source of truth. A successful CREATE or UPDATE also
synchronizes `contacts_fts` in the same SQLite transaction. Startup backfills
older contacts. If either the row or its FTS entry cannot be written, success is
not claimed.

Search has two distinct responsibilities:

```text
question → deterministic SQLite FTS5 retrieval (max 5 rows)
         → Groq phrases an answer only from those rows
```

FTS decides which stored evidence is relevant. Groq does not invent retrieval,
embed the query, or gain access to unrelated rows. With no FTS matches, the bot
answers deterministically and does not call Groq.

Default capture routes directly from a verified write to `finalize`. The vector
nodes remain an explicit-injection experiment and are not part of normal runtime.

**Check:** If `/search Who did I meet at LEAP?` finds no FTS rows, should Groq be
called? Why does keeping that decision deterministic matter?

---

## Task 10 — Reasoning stays behind the provider boundary

Telegram users should receive the answer, not the model's private reasoning.
The Groq request now asks Qwen to hide reasoning at the source. A small local
check is still necessary because older or mocked responses can contain a leading
`<think>...</think>` block.

That fallback accepts one complete leading reasoning block followed by a real
answer. It rejects reasoning-only, malformed, nested, or residual reasoning tags
instead of guessing which fragment is safe to show. This keeps failure handling
deterministic and prevents punctuation or reasoning text from reaching Telegram.

The cleanup belongs in `GroqSearchAnswerer`, the provider boundary, so every
caller receives the same safe final-answer contract. Telegram keeps its existing
`🔎 Search result` presentation and does not need model-specific parsing.

**Check:** Temporarily mock Groq to return
`<think>reason</think>\nYou met Mariana.` What should Telegram show? What should
happen if the returned final sentence contains another `<think>` tag?

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
                                  \               /
                                   finalize → END
```

When an `EmbeddingProvider` is explicitly injected, the retained experimental
branch may still run after `verify_write`; it is not part of this default graph.

---

## Tooling (how we work, not what the CRM is)

- **Ponytail:** smallest **code**. Does not skip teaching.
- **Graphify-Labs Graphify** (https://github.com/Graphify-Labs/graphify): query `graphify-out/` before exploring files, then teach from what you found.

Required reports after every specified task: Learning Step → Implementation Update → Evaluation → What You Should Understand Now. Then update this file and `progress_so_far.md`.
