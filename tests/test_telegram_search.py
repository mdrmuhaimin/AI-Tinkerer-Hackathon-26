import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from crm.storage import SQLiteContactStore
from crm.telegram_bot import NO_RESULTS_MESSAGE, SEARCH_PROMPT_MESSAGE, build_handlers
from tests.test_telegram_bot import FakeAttachment, make_update


def run(coro):
    return asyncio.run(coro)


class Answerer:
    def __init__(self): self.calls = []
    def answer(self, query, records):
        self.calls.append((query, records))
        return f"You met {records[0]['full_name']}."


def test_captionless_capture_formats_prints_and_persists(tmp_path, capsys):
    graph = Mock()
    graph.invoke.return_value = {
        "status": "complete", "errors": [],
        "contact_evidence": {"full_name": "Ada", "company": "Acme", "job_title": None,
                             "email": None, "phone": None, "website": None, "address": None},
        "voice_transcript": None, "conversation_notes": "Met at LEAP",
        "image_path": "/private/file", "extracted_card": {"secret": True},
    }
    store = SQLiteContactStore(tmp_path / "db.sqlite3")
    handlers = build_handlers({42}, graph, store, Answerer())
    image = make_update(photo=[FakeAttachment()], caption=None)
    done = make_update(text="/done", caption=None)
    run(handlers.intake(image, None)); run(handlers.done(done, None))

    assert graph.invoke.call_args.args[0]["name"] is None
    reply = done.effective_message.reply_text.await_args.args[0]
    assert "✅ Contact processed" in reply and "👤 Name: Ada" in reply and "🏢 Company: Acme" in reply
    assert "Email" not in reply and "null" not in reply
    output = capsys.readouterr().out
    assert '"status": "complete"' in output and "/private/file" not in output and "secret" not in output
    assert store.search(42, "LEAP")[0]["full_name"] == "Ada"


def test_search_inline_prompted_and_no_results(tmp_path):
    store = SQLiteContactStore(tmp_path / "db.sqlite3")
    store.save(42, {"contact_evidence": {"full_name": "Ada", "company": None, "job_title": None,
               "email": None, "phone": None, "website": None, "address": None},
               "voice_transcript": None, "conversation_notes": "Met at LEAP"})
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
