# How to Run — AI Conference CRM (Task 1)

This document describes how to set up and run what has been built so far: the **LangGraph skeleton** with a CLI and deterministic input validation.

No LLM, database, or embeddings are used yet.

---

## Prerequisites

- **Python 3.11 or newer**
- A terminal
- Git (to clone the repo)

Check your Python version:

```bash
python3 --version
```

---

## 1. Get the code

If you have not already cloned the repository:

```bash
git clone https://github.com/mdrmuhaimin/AI-Tinkerer-Hackathon-26.git
cd AI-Tinkerer-Hackathon-26
```

If you already have the repo locally, pull the latest changes:

```bash
git pull
```

---

## 2. Create a virtual environment

From the project root:

```bash
python3 -m venv .venv
```

Activate it:

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Install the package

Install the project in editable mode with dev dependencies (includes pytest):

```bash
pip install -e ".[dev]"
```

This installs:

- `langgraph` — graph orchestration
- `pytest` — test runner
- the `crm` CLI entry point (optional; see below)

---

## 4. Run the tests

From the project root:

```bash
pytest -q
```

Expected result:

```text
8 passed
```

The tests cover:

- Valid name + existing image path → `status: complete`
- Missing or blank name → `status: invalid`
- Missing or nonexistent image → `status: invalid`
- Optional voice path (absent, blank, or valid file)
- Graph node order via `graph.stream()`

---

## 5. Run the CLI

The main way to run the app:

```bash
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg
```

With an optional voice file:

```bash
python -m crm --name "Ada Lovelace" --image /path/to/card.jpg --voice /path/to/note.wav
```

If you installed the package, you can also use:

```bash
crm --name "Ada Lovelace" --image /path/to/card.jpg
```

### Use a real file for the image

The image path must point to an **existing file**. For a quick test, create a placeholder:

```bash
echo "placeholder" > /tmp/card.jpg
python -m crm --name "Ada Lovelace" --image /tmp/card.jpg
```

---

## 6. What the output looks like

On success, the CLI prints the **final graph state as JSON** and exits with code `0`:

```json
{
  "name": "Ada Lovelace",
  "image_path": "/tmp/card.jpg",
  "voice_path": null,
  "status": "complete",
  "errors": []
}
```

On validation failure, it still prints JSON but exits with code `1`:

```json
{
  "name": "   ",
  "image_path": "/tmp/card.jpg",
  "voice_path": null,
  "status": "invalid",
  "errors": [
    "name is required"
  ]
}
```

Check the exit code:

```bash
python -m crm --name "Ada Lovelace" --image /tmp/card.jpg
echo $?   # 0 on success

python -m crm --name "" --image /tmp/card.jpg
echo $?   # 1 on validation failure
```

---

## 7. What the graph does today

Current flow:

```text
START → load_input → validate_input → finalize → END
```

| Node            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `load_input`    | Copies CLI inputs into graph state                   |
| `validate_input`| Checks name, image file, optional voice file         |
| `finalize`      | Sets `status` to `complete` when validation passed   |

Validation rules:

- **Name** — required; blank or whitespace-only names fail
- **Image** — required; path must exist as a file
- **Voice** — optional; if provided, path must exist as a file

---

## 8. What is not implemented yet

The following are intentionally out of scope for Task 1:

- LLM / business-card extraction
- Voice transcription
- PostgreSQL or any database
- Embeddings / semantic search
- Duplicate detection
- Contact create/update storage

Those will come in later tasks when specified.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'crm'`**

- Activate the virtual environment and run `pip install -e ".[dev]"` again.

**`image file not found`**

- Use an absolute path or a path relative to your current directory.
- Confirm the file exists: `ls -l /path/to/card.jpg`

**Tests fail after pulling new code**

```bash
pip install -e ".[dev]"
pytest -q
```
