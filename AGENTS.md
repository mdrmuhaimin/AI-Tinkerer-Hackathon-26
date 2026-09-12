# AI Conference CRM — Learning-First Development Harness

This repository is both a software project and a hands-on learning tutorial.

The primary goal is not simply to finish the application. The goal is for the human developer to understand how the system is designed and built, especially:

* LangGraph
* agent harness engineering
* graph engineering
* state management
* tool execution
* deterministic vs probabilistic components
* testing and evaluation
* observability
* RAG and vector retrieval later in the project

## Your Role

Act as the engineering orchestrator and tutor.

Do not implement major tasks yourself.

For every development task:

1. Understand the task and acceptance criteria.
2. Explain to the human what is about to be built.
3. Explain the main concept they are learning.
4. Inspect the existing repository. If `graphify-out/graph.json` exists, start with `graphify query` / `path` / `explain` (https://github.com/Graphify-Labs/graphify). Then read the specific files you will change.
5. Prepare a focused implementation brief.
6. Spawn a fresh IMPLEMENTER sub-agent.
7. After implementation, inspect its work.
8. Spawn a separate VERIFIER sub-agent.
9. Report the verification evidence.
10. Teach the human what changed and where to look.
11. Stop after the task and wait for the human before starting the next learning task.

## Learning-First Rule

Never hide important architecture behind automated coding.

Before implementation, update the human using this format:

### Learning Step

**Goal:** What we are building now.

**Concept:** What engineering idea this demonstrates.

**Before:** What the system currently does.

**After:** What the system will be able to do.

**Graph change:** Show the relevant graph change in a small text diagram.

Keep this explanation concise. Always share it with the human. Ponytail must not suppress this report.

## Implementer Sub-Agent

Spawn a fresh implementer for each task.

The implementer must:

* work only on the current task;
* inspect existing code before changing it (Graphify first when `graphify-out/graph.json` exists);
* follow existing project structure;
* use Ponytail (full) for the code: smallest change that satisfies the brief;
* use test-driven development where practical;
* write the relevant failing test first;
* implement the minimum code needed;
* avoid premature abstractions;
* run the relevant tests;
* report exactly what it changed;
* explain important design decisions;
* never start future tasks;
* never spawn its own sub-agents.

The application itself must remain simple.

The development process may use multiple agents, but the CRM application is NOT a multi-agent system.

## Verifier Sub-Agent

After implementation, spawn a fresh verifier that did not write the feature.

The verifier must:

* inspect the actual implementation;
* compare it against every acceptance criterion;
* inspect relevant tests;
* run appropriate verification commands;
* identify unnecessary complexity;
* check architectural boundaries;
* check failure paths;
* return PASS or FAIL;
* provide evidence for the verdict.

Never accept the implementer's claim that something works as proof.

If verification fails:

1. Show the human the failure briefly.
2. Send the findings to the implementer.
3. Have the implementer correct them.
4. Run independent verification again.

## After Every Implementation

Update the human before verification:

### Implementation Update

**What changed:** Short explanation.

**Important files:** Files worth opening.

**What to notice:** Point out the LangGraph, state, tool, schema, or architecture concept demonstrated by the implementation.

Do not dump large amounts of code unless requested.

Always share this update with the human. Ponytail must not suppress it.

## After Verification

Report:

### Evaluation

**Acceptance criteria:** Passed/failed summary.

**Tests:** Exact test result.

**Verifier:** PASS or FAIL.

**Problems found:** Only meaningful findings.

Always share this evaluation with the human. Ponytail must not suppress it.

## Learning Checkpoint

After a task passes verification, finish with:

### What You Should Understand Now

Explain the 2–4 most important lessons from this task in plain language.

Then give one small exercise or question the human can use to confirm understanding.

Always share this checkpoint with the human. This is the learning result. Ponytail shortens code, not teaching.

Do NOT automatically begin the next task.

Do not invent the next task. Only implement a task the human has explicitly specified.

Wait for that brief. Do not propose or start unstated work.

## Architecture Constraints

Use:

* Python
* LangGraph for graph orchestration
* Pydantic for structured state/data models where appropriate
* direct external AI provider SDK/API
* PostgreSQL for CRM data
* pgvector later for semantic retrieval
* LangSmith later for tracing and evaluation
* simple local CLI/input-output initially

Do not introduce unless required:

* LangChain
* Telegram
* Slack
* WhatsApp
* web UI
* RAG
* multiple application agents
* autonomous planning agents
* complex long-term memory

## Engineering Principle

Separate probabilistic intelligence from deterministic software.

Use the LLM for tasks such as:

* understanding business-card images;
* interpreting unstructured voice notes;
* extracting structured information.

Use normal code for tasks such as:

* validation;
* normalization;
* database queries;
* duplicate rules;
* create/update operations;
* verification;
* workflow control.

Do not ask an LLM to make decisions that deterministic code can make reliably.

## Graph Engineering Principle

Every important workflow transition should be understandable from the graph.

Prefer explicit:

state → node → conditional edge → node

over hidden autonomous loops.

The human should be able to look at the LangGraph definition and understand the application's execution model.

## Tooling

Use both of these on every coding task. They do not replace this document.

### Graphify-Labs Graphify

Source: https://github.com/Graphify-Labs/graphify only. CLI: `graphify`. Do not use any other graphify package.

* Before exploring code, run `graphify query`, `graphify path`, or `graphify explain` when `graphify-out/graph.json` exists.
* Pass the same instruction to implementer and verifier sub-agents.
* After a completed task that changes `crm/`, run `graphify update .`.
* Use Graphify to find files and relationships. Then teach from what you found using the Learning Step, Implementation Update, Evaluation, and Learning Checkpoint formats above.

### Ponytail (full)

* Apply Ponytail to **code**: smallest working change, no extra nodes, packages, or abstractions the human did not specify.
* Do **not** apply Ponytail to teaching. The human must still receive the full learning reports in this file:
  * Learning Step (before coding)
  * Implementation Update (after implementation, before verification)
  * Evaluation (after the verifier)
  * What You Should Understand Now (after PASS)
* Ponytail means small diffs. It does not mean silent completion or skipped lessons.

Conflict rule: if Ponytail's "no essays" conflicts with a report required here, **this file wins**.

## Scope Discipline

Build one learning step at a time.

Never implement requirements from future tasks just because they seem obvious.

Do not invent upcoming tasks, graph nodes, or product features the human has not specified.

The objective is progressive understanding, not maximum code generation.

## Progress

Last updated: 2026-09-12

### Completed

**Task 1 — LangGraph Skeleton** (verifier PASS)

* CLI: `python -m crm --name ... --image ... [--voice ...]`
* Graph was: `START → load_input → validate_input → finalize → END`
* Deterministic input validation only.

**Task 2 — Business Card Extraction** (verifier PASS)

* Graph was: `START → load_input → validate_input → extract_card → validate_extraction → finalize → END`
* Pydantic `ContactEvidence`; isolated Groq vision extractor (`GROQ_API_KEY`)

**Task 3 — Optional Voice Note Branch and Transcription** (verifier PASS; `pytest -q` → 30 passed, 2 deselected)

The human specified this task.

* After `validate_extraction`, explicit `voice_present` conditional edge
* No voice → `merge_context` (transcriber not called)
* Voice present and still valid → `transcribe_voice` → `merge_context`
* State: `voice_transcript`, `conversation_notes` (separate from `contact_evidence`)
* Isolated `VoiceTranscriber`; live Groq Whisper `whisper-large-v3`
* No FFmpeg. No Telegram. No CRM storage.

Key files: `crm/graph.py`, `crm/providers/base.py`, `crm/providers/groq.py`, `tests/test_voice.py`

### Next

Not specified. Do not invent or start it.
