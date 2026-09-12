import os

from dotenv import load_dotenv

PROJECT = "ai-conference-crm"


def enable_tracing() -> None:
    load_dotenv()
    if not os.environ.get("LANGSMITH_API_KEY"):
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", PROJECT)
