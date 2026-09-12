# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 41 files · ~61,188 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 426 nodes · 1174 edges · 16 communities (13 shown, 1 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `99fb97b0`
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

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 56 edges
2. `_run()` - 49 edges
3. `FakeExtractor` - 43 edges
4. `ContactStore` - 39 edges
5. `CRMState` - 34 edges
6. `FakeTranscriber` - 34 edges
7. `FakeEmbedder` - 29 edges
8. `StoreError` - 26 edges
9. `ContactEvidence` - 20 edges
10. `_count()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `_count()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_run()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_graph()` --uses--> `ContactStore`  [INFERRED]
  tests/test_embeddings.py → crm/db.py
- `test_incorrect_stored_values_fail()` --uses--> `ContactStore`  [INFERRED]
  tests/test_verify.py → crm/db.py
- `test_merge_context_typed_and_voice_rules()` --calls--> `merge_context()`  [EXTRACTED]
  tests/test_voice.py → crm/graph.py

## Import Cycles
- None detected.

## Communities (16 total, 1 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 4)"
Cohesion: 0.05
Nodes (41): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 5b. Offline evaluation, 6. Run the CLI (+33 more)

### Community 1 - "ExtractorError"
Cohesion: 0.13
Nodes (21): extract_card_node(), transcribe_voice_node(), extract_card(), transcribe_voice(), CardExtractor, ExtractorError, Exception, Raised when business-card extraction fails. (+13 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.09
Nodes (22): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Completed, Engineering Principle, Evaluation, Graph Engineering Principle (+14 more)

### Community 3 - "test_eval.py"
Cohesion: 0.10
Nodes (38): create_vs_update(), duplicate_avoidance(), _eval_items(), _example_id(), _experiment_url(), extraction_correctness(), load_dataset(), main() (+30 more)

### Community 4 - "graph.py"
Cohesion: 0.11
Nodes (36): BaseModel, _blank(), build_graph(), search_crm_node(), store_embedding_node(), update_contact_node(), verify_write_node(), build_search_document() (+28 more)

### Community 5 - "FakeTranscriber"
Cohesion: 0.26
Nodes (18): FakeTranscriber, Exception, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq() (+10 more)

### Community 6 - "discord_bot.py"
Cohesion: 0.10
Nodes (20): _parse_args(), _run_query(), _format_capture(), Intake, is_image(), is_voice(), _join_notes(), main() (+12 more)

### Community 7 - "test_graph.py"
Cohesion: 0.56
Nodes (10): _graph(), _pending(), Path, _stream_node_names(), test_missing_or_blank_name_is_invalid(), test_missing_or_nonexistent_image_is_invalid(), test_stream_node_order_valid_and_invalid(), test_valid_name_and_image_completes() (+2 more)

### Community 8 - "FakeExtractor"
Cohesion: 0.25
Nodes (21): main(), FakeExtractor, _patch_graph(), test_cli_extractor_error_exits_1(), test_cli_invalid_prints_json_and_exits_1(), test_cli_module_smoke_invalid_avoids_provider(), test_cli_notes_and_voice_merge(), test_cli_notes_stored() (+13 more)

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

### Community 11 - "Discord DM adapter — plan for a later build"
Cohesion: 0.22
Nodes (7): Discord DM adapter — plan for a later build, Docs (when we build), Implementation (when we build), Out of scope, Process when building, Tests (when we build), User flow

### Community 14 - "_run"
Cohesion: 0.09
Nodes (63): EmbeddingProvider, build_search_document(), query_contacts(), FakeEmbedder, _count(), _pending(), MonkeyPatch, Path (+55 more)

### Community 15 - "ContactStore"
Cohesion: 0.08
Nodes (20): ContactStore, _Cursor, _ExtConnection, _now(), _prefer(), Exception, Path, sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it. (+12 more)

## Knowledge Gaps
- **66 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 114 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `ExtractorError`, `test_eval.py`, `FakeTranscriber`, `discord_bot.py`, `test_graph.py`, `FakeExtractor`, `_run`, `ContactStore`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `ContactStore` connect `ContactStore` to `test_eval.py`, `graph.py`, `discord_bot.py`, `_run`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
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