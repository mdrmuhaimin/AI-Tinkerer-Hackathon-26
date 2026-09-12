# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 41 files · ~61,714 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 436 nodes · 1196 edges · 21 communities (17 shown, 1 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `837dead6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- How to Run — AI Conference CRM (Task 4)
- ExtractorError
- AI Conference CRM — Learning-First Development Harness
- test_eval.py
- graph.py
- FakeTranscriber
- discord_bot.py
- test_graph.py
- FakeExtractor
- AI Conference CRM Agent
- Discord DM adapter — plan for a later build
- ai-conference-crm
- _run
- ContactStore
- Progress So Far — AI Conference CRM
- What You Should Understand So Far
- Progress
- Tooling

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 56 edges
2. `_run()` - 49 edges
3. `FakeExtractor` - 44 edges
4. `ContactStore` - 39 edges
5. `CRMState` - 34 edges
6. `FakeTranscriber` - 34 edges
7. `FakeEmbedder` - 29 edges
8. `StoreError` - 26 edges
9. `_count()` - 21 edges
10. `ContactEvidence` - 20 edges

## Surprising Connections (you probably didn't know these)
- `boom()` --calls--> `StoreError`  [EXTRACTED]
  tests/test_verify.py → crm/db.py
- `_count()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_run()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_graph()` --uses--> `ContactStore`  [INFERRED]
  tests/test_embeddings.py → crm/db.py
- `test_incorrect_stored_values_fail()` --uses--> `ContactStore`  [INFERRED]
  tests/test_verify.py → crm/db.py

## Import Cycles
- None detected.

## Communities (21 total, 1 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 4)"
Cohesion: 0.13
Nodes (15): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 5b. Offline evaluation, 6. Run the CLI (+7 more)

### Community 1 - "ExtractorError"
Cohesion: 0.08
Nodes (29): _run_query(), extract_card_node(), transcribe_voice_node(), extract_card(), transcribe_voice(), CardExtractor, EmbedderError, ExtractorError (+21 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.12
Nodes (16): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Engineering Principle, Evaluation, Graph Engineering Principle, Implementation Update (+8 more)

### Community 3 - "test_eval.py"
Cohesion: 0.09
Nodes (40): _parse_args(), create_vs_update(), duplicate_avoidance(), _eval_items(), _example_id(), _experiment_url(), extraction_correctness(), load_dataset() (+32 more)

### Community 4 - "graph.py"
Cohesion: 0.10
Nodes (39): BaseModel, _blank(), build_graph(), create_contact_node(), create_embedding_node(), search_crm_node(), update_contact_node(), verify_write_node() (+31 more)

### Community 5 - "FakeTranscriber"
Cohesion: 0.26
Nodes (18): FakeTranscriber, Exception, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq() (+10 more)

### Community 6 - "discord_bot.py"
Cohesion: 0.15
Nodes (12): _format_capture(), Intake, is_image(), is_voice(), _join_notes(), main(), on_message(), Pending (+4 more)

### Community 7 - "test_graph.py"
Cohesion: 0.53
Nodes (11): _graph(), _pending(), Path, _stream_node_names(), test_blank_name_is_taken_from_card(), test_missing_name_without_image_is_invalid(), test_missing_or_nonexistent_image_is_invalid(), test_stream_node_order_valid_and_invalid() (+3 more)

### Community 8 - "FakeExtractor"
Cohesion: 0.26
Nodes (20): main(), FakeExtractor, _patch_graph(), test_cli_extractor_error_exits_1(), test_cli_invalid_prints_json_and_exits_1(), test_cli_notes_and_voice_merge(), test_cli_notes_stored(), test_cli_valid_prints_json_status() (+12 more)

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

### Community 11 - "Discord DM adapter — plan for a later build"
Cohesion: 0.22
Nodes (7): Discord DM adapter — plan for a later build, Docs (when we build), Implementation (when we build), Out of scope, Process when building, Tests (when we build), User flow

### Community 14 - "_run"
Cohesion: 0.09
Nodes (62): query_contacts(), FakeEmbedder, _count(), _pending(), MonkeyPatch, Path, _run(), _store() (+54 more)

### Community 15 - "ContactStore"
Cohesion: 0.09
Nodes (19): ContactStore, _Cursor, _ExtConnection, _now(), _prefer(), Exception, Path, sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it. (+11 more)

### Community 16 - "Progress So Far — AI Conference CRM"
Cohesion: 0.13
Nodes (15): Discord DM adapter, Live checks, Progress So Far — AI Conference CRM, Task 1 — LangGraph Skeleton, Task 2 — Business Card Extraction, Task 3 — Optional Voice Note Branch and Transcription, Task 4 — SQLite CRM Persistence, Matching, and Notes, Task 6 — Semantic Contact Retrieval with sqlite-vec (+7 more)

### Community 17 - "What You Should Understand So Far"
Cohesion: 0.15
Nodes (13): Current graph (all tasks), Discord — another door, same rooms, Task 1 — LangGraph is state + nodes + edges, Task 2 — The model does not own the result, Task 3 — Voice is optional context, not identity, Task 4 — Persistence, keys, and notes, Task 6 — The vector is an index, not the record, Task 7 — A trace is not a score (+5 more)

### Community 19 - "Progress"
Cohesion: 0.67
Nodes (3): Completed, Next, Progress

### Community 20 - "Tooling"
Cohesion: 0.67
Nodes (3): Graphify-Labs Graphify, Ponytail (full), Tooling

## Knowledge Gaps
- **68 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 120 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `ExtractorError`, `test_eval.py`, `FakeTranscriber`, `discord_bot.py`, `test_graph.py`, `FakeExtractor`, `_run`, `ContactStore`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `ContactStore` connect `ContactStore` to `ExtractorError`, `test_eval.py`, `graph.py`, `discord_bot.py`, `_run`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `FakeExtractor` connect `FakeExtractor` to `test_eval.py`, `graph.py`, `FakeTranscriber`, `test_graph.py`, `_run`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `create_contact_node()` and `create_embedding_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FakeExtractor` (e.g. with `_patch_graph()` and `_graph()`) actually correct?**
  _`FakeExtractor` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ContactStore` (e.g. with `create_contact()` and `search_crm()`) actually correct?**
  _`ContactStore` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `CRMState` (e.g. with `build_graph()` and `build_search_document()`) actually correct?**
  _`CRMState` has 27 INFERRED edges - model-reasoned connections that need verification._