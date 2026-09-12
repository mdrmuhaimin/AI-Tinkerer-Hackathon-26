# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 38 files · ~59,031 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 386 nodes · 1071 edges · 14 communities (10 shown, 1 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b095d830`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- How to Run — AI Conference CRM (Task 4)
- test_cli.py
- AI Conference CRM — Learning-First Development Harness
- test_eval.py
- graph.py
- FakeTranscriber
- FakeExtractor
- AI Conference CRM Agent
- ai-conference-crm
- _run
- ContactStore

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 51 edges
2. `_run()` - 47 edges
3. `FakeExtractor` - 41 edges
4. `ContactStore` - 35 edges
5. `CRMState` - 34 edges
6. `FakeTranscriber` - 30 edges
7. `FakeEmbedder` - 27 edges
8. `StoreError` - 26 edges
9. `ContactEvidence` - 20 edges
10. `run_experiment()` - 18 edges

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

## Communities (14 total, 1 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 4)"
Cohesion: 0.05
Nodes (38): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 5b. Offline evaluation, 6. Run the CLI (+30 more)

### Community 1 - "test_cli.py"
Cohesion: 0.09
Nodes (34): _format_query_hits(), main(), _parse_args(), _run_query(), transcribe_voice(), EmbedderError, ExtractorError, Exception (+26 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.09
Nodes (22): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Completed, Engineering Principle, Evaluation, Graph Engineering Principle (+14 more)

### Community 3 - "test_eval.py"
Cohesion: 0.10
Nodes (38): create_vs_update(), duplicate_avoidance(), _eval_items(), _example_id(), _experiment_url(), extraction_correctness(), load_dataset(), main() (+30 more)

### Community 4 - "graph.py"
Cohesion: 0.08
Nodes (44): BaseModel, _blank(), build_graph(), create_contact_node(), create_embedding_node(), extract_card_node(), search_crm_node(), transcribe_voice_node() (+36 more)

### Community 5 - "FakeTranscriber"
Cohesion: 0.26
Nodes (18): FakeTranscriber, Exception, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq() (+10 more)

### Community 8 - "FakeExtractor"
Cohesion: 0.28
Nodes (20): FakeExtractor, _graph(), _pending(), Path, test_fake_extractor_error_sets_error_status(), test_fake_full_payload_matches_contact_evidence(), test_fake_invalid_payload_is_schema_invalid(), test_fake_only_full_name_does_not_invent_fields() (+12 more)

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

### Community 14 - "_run"
Cohesion: 0.10
Nodes (56): build_search_document(), query_contacts(), FakeEmbedder, test_query_ranked_list_does_not_run_graph_or_write(), _count(), _pending(), MonkeyPatch, Path (+48 more)

### Community 15 - "ContactStore"
Cohesion: 0.09
Nodes (19): ContactStore, _Cursor, _ExtConnection, _now(), _prefer(), Exception, Path, sqlite3-shaped wrapper so sqlite_vec.load() works when CPython omits it. (+11 more)

## Knowledge Gaps
- **57 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+52 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 100 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `graph.py` to `test_cli.py`, `test_eval.py`, `FakeTranscriber`, `FakeExtractor`, `_run`, `ContactStore`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `ContactStore` connect `ContactStore` to `test_cli.py`, `test_eval.py`, `graph.py`, `_run`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `FakeExtractor` connect `FakeExtractor` to `test_cli.py`, `test_eval.py`, `graph.py`, `FakeTranscriber`, `_run`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build_graph()` (e.g. with `create_contact_node()` and `create_embedding_node()`) actually correct?**
  _`build_graph()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FakeExtractor` (e.g. with `_patch_graph()` and `_graph()`) actually correct?**
  _`FakeExtractor` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ContactStore` (e.g. with `create_contact()` and `search_crm()`) actually correct?**
  _`ContactStore` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `CRMState` (e.g. with `build_graph()` and `build_search_document()`) actually correct?**
  _`CRMState` has 27 INFERRED edges - model-reasoned connections that need verification._