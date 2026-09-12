# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 33 files · ~54,663 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 324 nodes · 904 edges · 15 communities (10 shown, 2 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 104 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd0f0e64`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- How to Run — AI Conference CRM (Task 4)
- ExtractorError
- AI Conference CRM — Learning-First Development Harness
- _Cursor
- graph.py
- FakeTranscriber
- test_graph.py
- FakeExtractor
- AI Conference CRM Agent
- ai-conference-crm
- _run
- ContactStore

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 49 edges
2. `_run()` - 41 edges
3. `FakeExtractor` - 37 edges
4. `CRMState` - 34 edges
5. `ContactStore` - 33 edges
6. `StoreError` - 26 edges
7. `FakeTranscriber` - 25 edges
8. `FakeEmbedder` - 23 edges
9. `ContactEvidence` - 20 edges
10. `ExtractorError` - 18 edges

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

## Communities (15 total, 2 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 4)"
Cohesion: 0.06
Nodes (33): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 6. Run the CLI, 7. What the output looks like (+25 more)

### Community 1 - "ExtractorError"
Cohesion: 0.09
Nodes (30): _parse_args(), _run_query(), create_embedding_node(), extract_card_node(), transcribe_voice_node(), create_embedding(), extract_card(), transcribe_voice() (+22 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.09
Nodes (22): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Completed, Engineering Principle, Evaluation, Graph Engineering Principle (+14 more)

### Community 4 - "graph.py"
Cohesion: 0.11
Nodes (36): BaseModel, _blank(), build_graph(), create_contact_node(), store_embedding_node(), update_contact_node(), verify_write_node(), build_search_document() (+28 more)

### Community 5 - "FakeTranscriber"
Cohesion: 0.27
Nodes (15): FakeTranscriber, Exception, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq() (+7 more)

### Community 7 - "test_graph.py"
Cohesion: 0.56
Nodes (10): _graph(), _pending(), Path, _stream_node_names(), test_missing_or_blank_name_is_invalid(), test_missing_or_nonexistent_image_is_invalid(), test_stream_node_order_valid_and_invalid(), test_valid_name_and_image_completes() (+2 more)

### Community 8 - "FakeExtractor"
Cohesion: 0.29
Nodes (18): main(), FakeExtractor, _patch_graph(), test_cli_extractor_error_exits_1(), test_cli_invalid_prints_json_and_exits_1(), test_cli_module_smoke_invalid_avoids_provider(), test_cli_valid_prints_json_status(), test_cli_voice_prints_transcript_and_notes() (+10 more)

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

### Community 14 - "_run"
Cohesion: 0.11
Nodes (50): build_search_document(), FakeEmbedder, _count(), _pending(), MonkeyPatch, Path, _run(), _store() (+42 more)

### Community 15 - "ContactStore"
Cohesion: 0.12
Nodes (17): ContactStore, _ExtConnection, _now(), _prefer(), Exception, Path, sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it., StoreError (+9 more)

## Knowledge Gaps
- **52 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+47 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 91 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `ExtractorError`, `FakeTranscriber`, `test_graph.py`, `FakeExtractor`, `_run`, `ContactStore`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `ContactStore` connect `ContactStore` to `ExtractorError`, `graph.py`, `_run`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `FakeExtractor` connect `FakeExtractor` to `graph.py`, `FakeTranscriber`, `_run`, `test_graph.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `create_contact_node()` and `create_embedding_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FakeExtractor` (e.g. with `_patch_graph()` and `_graph()`) actually correct?**
  _`FakeExtractor` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `CRMState` (e.g. with `build_graph()` and `build_search_document()`) actually correct?**
  _`CRMState` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ContactStore` (e.g. with `create_contact()` and `search_crm()`) actually correct?**
  _`ContactStore` has 10 INFERRED edges - model-reasoned connections that need verification._