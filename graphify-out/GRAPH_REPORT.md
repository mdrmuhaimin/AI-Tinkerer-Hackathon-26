# Graph Report - AI-CRM  (2026-09-12)

## Corpus Check
- 25 files · ~48,904 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 175 nodes · 422 edges · 14 communities (10 shown, 1 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6f9b3354`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- How to Run — AI Conference CRM (Task 3)
- ExtractorError
- AI Conference CRM — Learning-First Development Harness
- test_cli.py
- build_graph
- test_voice.py
- ContactEvidence
- FakeExtractor
- test_extract.py
- AI Conference CRM Agent
- ai-conference-crm

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 30 edges
2. `FakeExtractor` - 27 edges
3. `ContactEvidence` - 20 edges
4. `CRMState` - 20 edges
5. `ExtractorError` - 18 edges
6. `FakeTranscriber` - 16 edges
7. `TranscriberError` - 15 edges
8. `AI Conference CRM — Learning-First Development Harness` - 14 edges
9. `How to Run — AI Conference CRM (Task 3)` - 13 edges
10. `GroqVoiceTranscriber` - 12 edges

## Surprising Connections (you probably didn't know these)
- `test_fake_full_payload_matches_contact_evidence()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_extract.py → crm/schemas.py
- `test_live_transcribe_voice_note()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_live_transcribe.py → crm/schemas.py
- `test_empty_optional_strings_normalize_to_null()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_schema.py → crm/schemas.py
- `test_full_name_required_and_blank_fails()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_schema.py → crm/schemas.py
- `test_full_valid_payload()` --uses--> `ContactEvidence`  [INFERRED]
  tests/test_schema.py → crm/schemas.py

## Import Cycles
- None detected.

## Communities (14 total, 1 thin omitted)

### Community 0 - "How to Run — AI Conference CRM (Task 3)"
Cohesion: 0.08
Nodes (22): 10. What is not implemented yet, 1. Get the code, 2. Create a virtual environment, 3. Install the package, 4. Run the tests, 5. Provider environment variables, 6. Run the CLI, 7. What the output looks like (+14 more)

### Community 1 - "ExtractorError"
Cohesion: 0.19
Nodes (13): ExtractorError, Exception, Raised when business-card extraction fails., Raised when voice transcription fails., TranscriberError, _encode_image(), GroqCardExtractor, GroqVoiceTranscriber (+5 more)

### Community 2 - "AI Conference CRM — Learning-First Development Harness"
Cohesion: 0.10
Nodes (20): After Every Implementation, After Verification, AI Conference CRM — Learning-First Development Harness, Architecture Constraints, Completed, Engineering Principle, Evaluation, Graph Engineering Principle (+12 more)

### Community 3 - "test_cli.py"
Cohesion: 0.36
Nodes (10): main(), _parse_args(), Namespace, _patch_graph(), test_cli_extractor_error_exits_1(), test_cli_invalid_prints_json_and_exits_1(), test_cli_module_smoke_invalid_avoids_provider(), test_cli_valid_prints_json_status() (+2 more)

### Community 4 - "build_graph"
Cohesion: 0.21
Nodes (17): _blank(), build_graph(), extract_card_node(), transcribe_voice_node(), extract_card(), finalize(), load_input(), merge_context() (+9 more)

### Community 5 - "test_voice.py"
Cohesion: 0.38
Nodes (14): FakeTranscriber, _graph(), _pending(), MonkeyPatch, Path, _stream_node_names(), test_default_suite_does_not_construct_live_groq(), test_name_and_image_without_voice_completes() (+6 more)

### Community 6 - "ContactEvidence"
Cohesion: 0.24
Nodes (9): BaseModel, ContactEvidence, field_validator, test_live_extract_visiting_card(), test_empty_optional_strings_normalize_to_null(), test_full_name_required_and_blank_fails(), test_full_valid_payload(), test_no_email_or_phone_format_validators() (+1 more)

### Community 7 - "FakeExtractor"
Cohesion: 0.26
Nodes (13): FakeExtractor, Exception, _graph(), _pending(), Path, _stream_node_names(), test_missing_or_blank_name_is_invalid(), test_missing_or_nonexistent_image_is_invalid() (+5 more)

### Community 8 - "test_extract.py"
Cohesion: 0.64
Nodes (8): _pending(), Path, test_fake_extractor_error_sets_error_status(), test_fake_full_payload_matches_contact_evidence(), test_fake_invalid_payload_is_schema_invalid(), test_fake_only_full_name_does_not_invent_fields(), test_invalid_input_does_not_call_extractor(), _touch()

### Community 9 - "AI Conference CRM Agent"
Cohesion: 0.25
Nodes (7): AI Conference CRM Agent, Context, First-Version Boundary, Success, The Intended Experience, What We Are Solving, Why AI Is Useful Here

## Knowledge Gaps
- **41 isolated node(s):** `ai-conference-crm`, `Your Role`, `Learning Step`, `Implementer Sub-Agent`, `Verifier Sub-Agent` (+36 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 63 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ContactEvidence` connect `ContactEvidence` to `test_extract.py`, `build_graph`, `test_voice.py`, `FakeExtractor`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `build_graph` to `test_cli.py`, `test_voice.py`, `ContactEvidence`, `FakeExtractor`, `test_extract.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `FakeExtractor` connect `FakeExtractor` to `test_extract.py`, `test_cli.py`, `test_voice.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `build_graph()` (e.g. with `extract_card_node()` and `transcribe_voice_node()`) actually correct?**
  _`build_graph()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ContactEvidence` (e.g. with `validate_extraction()` and `test_fake_full_payload_matches_contact_evidence()`) actually correct?**
  _`ContactEvidence` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `CRMState` (e.g. with `build_graph()` and `extract_card()`) actually correct?**
  _`CRMState` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ExtractorError` (e.g. with `extract_card()` and `GroqCardExtractor`) actually correct?**
  _`ExtractorError` has 3 INFERRED edges - model-reasoned connections that need verification._