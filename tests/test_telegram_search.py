import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from crm.db import ContactStore
from crm.graph import build_graph
from crm.providers.groq import GroqSearchAnswerer
from crm.telegram_bot import (
    GROUP_MESSAGE,
    NO_RESULTS_MESSAGE,
    SEARCH_ERROR_MESSAGE,
    SEARCH_PROMPT_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    build_handlers,
)
from tests.helpers import FakeExtractor, FakeTranscriber
from tests.test_telegram_bot import FakeAttachment, make_update


def run(coro):
    return asyncio.run(coro)


class Answerer:
    def __init__(self): self.calls = []
    def answer(self, query, records):
        self.calls.append((query, records))
        return f"You met {records[0]['full_name']}."


def test_captionless_capture_formats_prints_and_persists(tmp_path, capsys):
    evidence = {"full_name": "Ada", "company": "Acme", "job_title": None,
                "email": None, "phone": None, "website": None, "address": None}
    store = ContactStore(tmp_path / "db.sqlite3")
    graph = build_graph(extractor=FakeExtractor(evidence), transcriber=FakeTranscriber(), store=store)
    handlers = build_handlers({42}, graph, store, Answerer())
    image = make_update(photo=[FakeAttachment()], caption=None)
    done = make_update(text="/done", caption=None)
    run(handlers.intake(image, None)); run(handlers.done(done, None))

    reply = done.effective_message.reply_text.await_args.args[0]
    assert "✅ Contact processed" in reply and "👤 Name: Ada" in reply and "🏢 Company: Acme" in reply
    assert "Email" not in reply and "null" not in reply
    output = capsys.readouterr().out
    assert '"status": "complete"' in output and "image_path" not in output and "extracted_card" not in output
    assert store.search("Ada")[0]["full_name"] == "Ada"
    assert len(store.search("Ada")) == 1


def test_search_inline_prompted_and_no_results(tmp_path):
    store = ContactStore(tmp_path / "db.sqlite3")
    store.create({"full_name": "Ada", "company": None, "job_title": None,
                  "email": None, "phone": None, "website": None, "address": None,
                  "notes": "Met at LEAP"})
    answerer = Answerer(); handlers = build_handlers({42}, Mock(), store, answerer)
    inline = make_update(text="/search who did I meet at LEAP?", caption=None)
    run(handlers.search(inline, None))
    assert "You met Ada" in inline.effective_message.reply_text.await_args.args[0]

    command = make_update(text="/search", caption=None)
    run(handlers.search(command, None))
    command.effective_message.reply_text.assert_awaited_once_with(SEARCH_PROMPT_MESSAGE)
    followup = make_update(text="LEAP", caption=None)
    run(handlers.text(followup, None))
    assert "You met Ada" in followup.effective_message.reply_text.await_args.args[0]

    missing = make_update(text="/search nowhere", caption=None)
    calls = len(answerer.calls); run(handlers.search(missing, None))
    missing.effective_message.reply_text.assert_awaited_once_with(NO_RESULTS_MESSAGE)
    assert len(answerer.calls) == calls


def test_search_answerer_failure_is_safe(tmp_path):
    store = ContactStore(tmp_path / "db.sqlite3")
    store.create({**{"full_name": "Ada", "notes": "LEAP"},
                  **{field: None for field in ("company", "job_title", "email", "phone", "website", "address")}})
    answerer = Mock()
    answerer.answer.side_effect = RuntimeError("secret")
    update = make_update(text="/search LEAP", caption=None)
    run(build_handlers({42}, Mock(), store, answerer).search(update, None))
    update.effective_message.reply_text.assert_awaited_once_with(SEARCH_ERROR_MESSAGE)


def test_search_rejects_residual_reasoning_from_provider(tmp_path, monkeypatch):
    store = ContactStore(tmp_path / "db.sqlite3")
    store.create({**{"full_name": "Mariana", "notes": "community meetup"},
                  **{field: None for field in ("company", "job_title", "email", "phone", "website", "address")}})

    class _Completions:
        def create(self, **_kwargs):
            message = type("Message", (), {
                "content": "<think>reason</think>\nYou met <think>Mariana</think>."
            })()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class _Client:
        def __init__(self, **_kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr("crm.providers.groq.Groq", _Client)
    update = make_update(text="/search community meetup", caption=None)
    handlers = build_handlers(
        {42}, Mock(), store, GroqSearchAnswerer(api_key="test-key")
    )

    run(handlers.search(update, None))

    update.effective_message.reply_text.assert_awaited_once_with(SEARCH_ERROR_MESSAGE)


def test_search_enforces_private_allowlist(tmp_path):
    handlers = build_handlers({42}, Mock(), ContactStore(tmp_path / "db.sqlite3"), Answerer())
    unauthorized = make_update(user_id=99, text="/search LEAP", caption=None)
    group = make_update(chat_type="group", text="/search LEAP", caption=None)
    run(handlers.search(unauthorized, None))
    run(handlers.search(group, None))
    unauthorized.effective_message.reply_text.assert_awaited_once_with(UNAUTHORIZED_MESSAGE)
    group.effective_message.reply_text.assert_awaited_once_with(GROUP_MESSAGE)


def test_long_search_answer_uses_utf16_safe_chunks(tmp_path):
    store = ContactStore(tmp_path / "db.sqlite3")
    store.create({**{"full_name": "Ada", "notes": "LEAP"},
                  **{field: None for field in ("company", "job_title", "email", "phone", "website", "address")}})
    answerer = Answerer()
    answerer.answer = lambda query, records: "🚀 result " * 1000
    update = make_update(text="/search LEAP", caption=None)
    run(build_handlers({42}, Mock(), store, answerer).search(update, None))
    chunks = [call.args[0] for call in update.effective_message.reply_text.await_args_list]
    assert len(chunks) > 1
    assert all(len(chunk.encode("utf-16-le")) // 2 <= 3500 for chunk in chunks)
