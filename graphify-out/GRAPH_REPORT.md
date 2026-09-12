# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 38 files · ~57,525 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 369 nodes · 1010 edges · 15 communities (11 shown, 1 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 112 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5254531c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- How to Run — AI Conference CRM (Task 4)
- ExtractorError
- AI Conference CRM — Learning-First Development Harness
- test_eval.py
- graph.py
- FakeTranscriber
- test_cli.py
- FakeExtractor
- AI Conference CRM Agent
- ai-conference-crm
- _run
- ContactStore

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 51 edges
2. `_run()` - 41 edges
3. `FakeExtractor` - 39 edges
4. `ContactStore` - 35 edges
5. `CRMState` - 34 edges
6. `FakeTranscriber` - 27 edges
7. `StoreError` - 26 edges
8. `FakeEmbedder` - 25 edges
9. `ContactEvidence` - 20 edges
10. `ExtractorError` - 18 edges

## Surprising Connections (you probably didn't know these)
- `_count()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_run()` --uses--> `ContactStore`  [INFERRED]
  tests/test_crm.py → crm/db.py
- `_graph()` --uses--> `ContactStore`  [INFERRED]
  tests/test_embeddings.py → crm/db.py
- `test_incorrect_stored_values_fail()` --uses--> `ContactStore`  [INFERRED]
  tests/test_verify.py → crm/db.py
- `test_fake_full_payload_matches_contact_evidence()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_extract.py → crm/schemas.py

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 4)"
Cohesion: 0.05
Nodes (36): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 5b. Offline evaluation, 6. Run the CLI (+28 more)

### Community 1 - "ExtractorError"
Cohesion: 0.12
Nodes (23): extract_card_node(), transcribe_voice_node(), extract_card(), transcribe_voice(), CardExtractor, EmbedderError, ExtractorError, Exception (+15 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.09
Nodes (22): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Completed, Engineering Principle, Evaluation, Graph Engineering Principle (+14 more)

### Community 3 - "test_eval.py"
Cohesion: 0.11
Nodes (35): create_vs_update(), duplicate_avoidance(), _eval_items(), _example_id(), _experiment_url(), extraction_correctness(), load_dataset(), main() (+27 more)

### Community 4 - "graph.py"
Cohesion: 0.09
Nodes (41): BaseModel, _blank(), build_graph(), create_contact_node(), create_embedding_node(), search_crm_node(), store_embedding_node(), update_contact_node() (+33 more)

### Community 5 - "FakeTranscriber"
Cohesion: 0.27
Nodes (15): FakeTranscriber, Exception, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq() (+7 more)

### Community 6 - "test_cli.py"
Cohesion: 0.22
Nodes (13): main(), _parse_args(), _run_query(), GroqEmbedder, traceable, Namespace, _patch_graph(), test_cli_extractor_error_exits_1() (+5 more)

### Community 8 - "FakeExtractor"
Cohesion: 0.28
Nodes (20): FakeExtractor, _graph(), _pending(), Path, test_fake_extractor_error_sets_error_status(), test_fake_full_payload_matches_contact_evidence(), test_fake_invalid_payload_is_schema_invalid(), test_fake_only_full_name_does_not_invent_fields() (+12 more)

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

### Community 14 - "_run"
Cohesion: 0.11
Nodes (50): build_search_document(), query_contacts(), FakeEmbedder, _count(), _pending(), MonkeyPatch, Path, _run() (+42 more)

### Community 15 - "ContactStore"
Cohesion: 0.09
Nodes (18): ContactStore, _Cursor, _ExtConnection, _now(), _prefer(), Exception, Path, sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it. (+10 more)

## Knowledge Gaps
- **55 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 97 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `ExtractorError`, `test_eval.py`, `FakeTranscriber`, `test_cli.py`, `FakeExtractor`, `_run`, `ContactStore`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `ContactStore` connect `ContactStore` to `test_eval.py`, `graph.py`, `test_cli.py`, `_run`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `FakeExtractor` connect `FakeExtractor` to `test_eval.py`, `graph.py`, `FakeTranscriber`, `test_cli.py`, `_run`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `create_contact_node()` and `create_embedding_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FakeExtractor` (e.g. with `_patch_graph()` and `_graph()`) actually correct?**
  _`FakeExtractor` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ContactStore` (e.g. with `create_contact()` and `search_crm()`) actually correct?**
  _`ContactStore` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `CRMState` (e.g. with `build_graph()` and `build_search_document()`) actually correct?**
  _`CRMState` has 27 INFERRED edges - model-reasoned connections that need verification._