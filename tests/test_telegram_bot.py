import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from crm.telegram_bot import (
    DOWNLOAD_ERROR_MESSAGE,
    CARD_RECEIVED_MESSAGE,
    GENERIC_ERROR_MESSAGE,
    GROUP_MESSAGE,
    HELP_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    UNSUPPORTED_MESSAGE,
    TelegramBotConfig,
    build_handlers,
    create_application,
    load_config,
    main,
)


class FakeAttachment:
    def __init__(self, content: bytes = b"image", *, download_error=None):
        self.content = content
        self.download_error = download_error

    async def get_file(self, **kwargs):
        attachment = self

        class File:
            async def download_to_drive(self, custom_path, **kwargs):
                if attachment.download_error:
                    raise attachment.download_error
                Path(custom_path).write_bytes(attachment.content)

        return File()


def make_update(
    *,
    user_id=42,
    chat_type="private",
    caption="Ada Lovelace",
    photo=None,
    document=None,
    text=None,
    voice=None,
    media_group_id=None,
    chat_id=100,
):
    message = SimpleNamespace(
        caption=caption,
        photo=photo or [],
        document=document,
        voice=voice,
        text=text,
        media_group_id=media_group_id,
        reply_text=AsyncMock(),
    )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(type=chat_type, id=chat_id),
        effective_message=message,
    )


def run(coro):
    return asyncio.run(coro)


def test_photo_queues_then_voice_maps_to_graph_while_files_exist_and_cleans_up(capsys):
    seen = {}

    class Graph:
        def invoke(self, state):
            seen.update(state)
            seen["files_exist"] = (
                Path(state["image_path"]).is_file(),
                Path(state["voice_path"]).is_file(),
            )
            return {
                **state,
                "status": "complete",
                "errors": [],
                "contact_evidence": {"full_name": "Ada Lovelace"},
                "voice_transcript": "Met at the conference.",
                "conversation_notes": "Met at the conference.",
            }

    update = make_update(photo=[FakeAttachment(b"card")], caption="  Ada Lovelace  ")
    handlers = build_handlers({42}, Graph())

    run(handlers.intake(update, None))
    graph_result_message = make_update(voice=FakeAttachment(b"voice"), caption=None)
    assert seen == {}
    update.effective_message.reply_text.assert_awaited_once_with(CARD_RECEIVED_MESSAGE)
    run(handlers.voice(graph_result_message, None))

    assert seen == {
        "name": "Ada Lovelace",
        "image_path": seen["image_path"],
        "voice_path": seen["voice_path"],
        "status": "pending",
        "errors": [],
        "files_exist": (True, True),
    }
    assert not Path(seen["image_path"]).exists()
    assert not Path(seen["voice_path"]).exists()
    reply = graph_result_message.effective_message.reply_text.await_args.args[0]
    assert "👤 Name: Ada Lovelace" in reply
    assert "Met at the conference." in reply
    payload = json.loads(capsys.readouterr().out)
    assert list(payload) == list(("status", "errors", "contact_evidence", "voice_transcript", "conversation_notes"))


@pytest.mark.parametrize(
    ("mime_type", "file_name"),
    [("image/jpeg", "card.jpg"), ("image/png", "card.png")],
)
def test_supported_image_document_maps_to_graph(mime_type, file_name):
    graph = Mock()
    document = FakeAttachment()
    document.mime_type = mime_type
    document.file_name = file_name
    update = make_update(document=document)

    handlers = build_handlers({42}, graph)
    run(handlers.intake(update, None))

    graph.invoke.assert_not_called()
    expected_suffix = ".png" if mime_type == "image/png" else ".jpg"
    assert handlers.pending[100].image_path.endswith(expected_suffix)
    run(handlers.done(make_update(text="/done", caption=None), None))


def test_done_invokes_without_voice_and_returns_formatted_contact(capsys):
    graph = Mock()
    graph.invoke.return_value = {
        "status": "complete", "errors": [],
        "contact_evidence": {"full_name": "Ada Lovelace"},
        "voice_transcript": None, "conversation_notes": None,
        "image_path": "/secret/path", "extracted_card": {"raw": True},
    }
    handlers = build_handlers({42}, graph)
    image = make_update(photo=[FakeAttachment()])
    done = make_update(text="/done", caption=None)

    run(handlers.intake(image, None))
    queued_path = handlers.pending[100].image_path
    assert queued_path.endswith(".jpg")
    run(handlers.done(done, None))

    state = graph.invoke.call_args.args[0]
    assert state["voice_path"] is None
    assert not Path(queued_path).exists()
    assert "👤 Name: Ada Lovelace" in done.effective_message.reply_text.await_args.args[0]
    assert json.loads(capsys.readouterr().out) == {
        "status": "complete", "errors": [],
        "contact_evidence": {"full_name": "Ada Lovelace"},
        "voice_transcript": None, "conversation_notes": None,
    }


def test_voice_and_done_without_pending_do_not_invoke_graph():
    graph = Mock()
    handlers = build_handlers({42}, graph)
    voice = make_update(voice=FakeAttachment(), caption=None)
    done = make_update(text="/done", caption=None)
    run(handlers.voice(voice, None))
    run(handlers.done(done, None))
    graph.invoke.assert_not_called()
    assert "business-card" in voice.effective_message.reply_text.await_args.args[0]
    assert "business-card" in done.effective_message.reply_text.await_args.args[0]


def test_pending_intakes_are_isolated_and_replacement_cleans_old_file():
    handlers = build_handlers({42}, Mock())
    first = make_update(photo=[FakeAttachment(b"first")], chat_id=100)
    other = make_update(photo=[FakeAttachment(b"other")], chat_id=200)
    replacement = make_update(photo=[FakeAttachment(b"second")], chat_id=100)
    run(handlers.intake(first, None))
    first_path = handlers.pending[100].image_path
    run(handlers.intake(other, None))
    run(handlers.intake(replacement, None))
    assert not Path(first_path).exists()
    assert Path(handlers.pending[100].image_path).read_bytes() == b"second"
    assert Path(handlers.pending[200].image_path).read_bytes() == b"other"
    run(handlers.done(make_update(text="/done", caption=None, chat_id=100), None))
    run(handlers.done(make_update(text="/done", caption=None, chat_id=200), None))


def test_voice_download_failure_keeps_card_for_retry():
    graph = Mock()
    handlers = build_handlers({42}, graph)
    run(handlers.intake(make_update(photo=[FakeAttachment()]), None))
    card_path = handlers.pending[100].image_path
    voice = make_update(voice=FakeAttachment(download_error=RuntimeError("network")), caption=None)
    run(handlers.voice(voice, None))
    graph.invoke.assert_not_called()
    assert Path(card_path).exists()
    assert 100 in handlers.pending
    run(handlers.done(make_update(text="/done", caption=None), None))


@pytest.mark.parametrize("callback_name", ["voice", "done"])
def test_new_handlers_enforce_access(callback_name):
    graph = Mock()
    handlers = build_handlers({42}, graph)
    update = make_update(
        user_id=99, caption=None, text="/done",
        voice=FakeAttachment() if callback_name == "voice" else None,
    )
    run(getattr(handlers, callback_name)(update, None))
    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(UNAUTHORIZED_MESSAGE)


def test_application_registers_done_before_media_and_voice_handlers():
    application = create_application(TelegramBotConfig("123:TEST", frozenset({42})), Mock())
    callbacks = [handler.callback.__name__ for handler in application.handlers[0]]
    assert callbacks == [
        "help_handler", "done_handler", "search_handler", "intake_handler", "voice_handler",
        "text_handler",
        "unsupported_handler",
    ]


def test_graph_exception_cleans_pending_files():
    graph = Mock()
    graph.invoke.side_effect = RuntimeError("provider secret")
    handlers = build_handlers({42}, graph)
    run(handlers.intake(make_update(photo=[FakeAttachment()]), None))
    card_path = handlers.pending[100].image_path
    voice = make_update(voice=FakeAttachment(), caption=None)
    run(handlers.voice(voice, None))
    assert 100 not in handlers.pending
    assert not Path(card_path).exists()
    voice.effective_message.reply_text.assert_awaited_once_with(GENERIC_ERROR_MESSAGE)


def test_graph_errors_are_safe_without_internal_details(capsys):
    graph = Mock()
    graph.invoke.return_value = {
        "status": "error",
        "errors": ["voice transcription failed: /tmp/private.ogg API key abc"],
        "contact_evidence": {"full_name": "Ada"},
        "voice_transcript": None,
        "conversation_notes": None,
    }
    handlers = build_handlers({42}, graph)
    run(handlers.intake(make_update(photo=[FakeAttachment()]), None))
    done = make_update(text="/done", caption=None)
    run(handlers.done(done, None))
    output = done.effective_message.reply_text.await_args.args[0]
    assert "/tmp" not in output and "abc" not in output
    assert "voice note could not be validated" in output
    assert json.loads(capsys.readouterr().out)["errors"] == ["voice note could not be validated"]


def test_long_formatted_reply_is_sent_in_ordered_safe_chunks_without_data_loss():
    transcript = "Met at conference 🚀 " * 500
    graph = Mock()
    graph.invoke.return_value = {
        "status": "complete",
        "errors": [],
        "contact_evidence": {"full_name": "Ada Lovelace"},
        "voice_transcript": transcript,
        "conversation_notes": transcript,
    }
    handlers = build_handlers({42}, graph)
    run(handlers.intake(make_update(photo=[FakeAttachment()]), None))
    done = make_update(text="/done", caption=None)

    run(handlers.done(done, None))

    chunks = [call.args[0] for call in done.effective_message.reply_text.await_args_list]
    assert len(chunks) > 1
    assert all(len(chunk.encode("utf-16-le")) // 2 <= 3500 for chunk in chunks)
    reply = "".join(chunks)
    assert "👤 Name: Ada Lovelace" in reply
    assert transcript in reply


def test_missing_caption_is_accepted_and_queued():
    graph = Mock()
    update = make_update(photo=[FakeAttachment()], caption="  ")

    handlers = build_handlers({42}, graph)
    run(handlers.intake(update, None))

    graph.invoke.assert_not_called()
    assert handlers.pending[100].name is None
    update.effective_message.reply_text.assert_awaited_once_with(CARD_RECEIVED_MESSAGE)
    run(handlers.done(make_update(text="/done", caption=None), None))


def test_help_and_text_only_explain_input_format():
    handlers = build_handlers({42}, Mock())
    help_update = make_update(text="/start", caption=None)
    text_update = make_update(text="Ada Lovelace", caption=None)

    run(handlers.help(help_update, None))
    run(handlers.unsupported(text_update, None))

    help_update.effective_message.reply_text.assert_awaited_once_with(HELP_MESSAGE)
    text_update.effective_message.reply_text.assert_awaited_once_with(
        UNSUPPORTED_MESSAGE
    )


def test_unsupported_document_is_rejected():
    graph = Mock()
    document = FakeAttachment()
    document.mime_type = "application/pdf"
    document.file_name = "card.pdf"
    update = make_update(document=document)

    run(build_handlers({42}, graph).intake(update, None))

    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(UNSUPPORTED_MESSAGE)


@pytest.mark.parametrize(
    ("user_id", "chat_type", "expected"),
    [(99, "private", UNAUTHORIZED_MESSAGE), (42, "group", GROUP_MESSAGE)],
)
def test_access_is_restricted(user_id, chat_type, expected):
    graph = Mock()
    update = make_update(user_id=user_id, chat_type=chat_type, photo=[FakeAttachment()])

    run(build_handlers({42}, graph).intake(update, None))

    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(expected)


def test_album_is_rejected():
    graph = Mock()
    update = make_update(photo=[FakeAttachment()], media_group_id="album-1")

    run(build_handlers({42}, graph).intake(update, None))

    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(UNSUPPORTED_MESSAGE)


def test_download_error_asks_user_to_resend():
    graph = Mock()
    update = make_update(photo=[FakeAttachment(download_error=RuntimeError("network"))])

    run(build_handlers({42}, graph).intake(update, None))

    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(
        DOWNLOAD_ERROR_MESSAGE
    )


def test_graph_rejection_does_not_expose_file_path(capsys):
    class Graph:
        def invoke(self, state):
            return {
                **state,
                "status": "invalid",
                "errors": [f"image file not found: {state['image_path']}"],
            }

    update = make_update(photo=[FakeAttachment()])

    handlers = build_handlers({42}, Graph())
    run(handlers.intake(update, None))
    done = make_update(text="/done", caption=None)
    run(handlers.done(done, None))

    reply = done.effective_message.reply_text.await_args.args[0]
    assert "/tmp" not in reply and "/var" not in reply
    assert "image could not be validated" in reply
    assert json.loads(capsys.readouterr().out)["errors"] == ["image could not be validated"]


def test_unexpected_graph_exception_is_generic():
    seen = {}

    class Graph:
        def invoke(self, state):
            seen.update(state)
            raise ValueError("secret internal detail")

    update = make_update(photo=[FakeAttachment()])

    handlers = build_handlers({42}, Graph())
    run(handlers.intake(update, None))
    queued_path = handlers.pending[100].image_path
    done = make_update(text="/done", caption=None)
    run(handlers.done(done, None))

    done.effective_message.reply_text.assert_awaited_once_with(GENERIC_ERROR_MESSAGE)
    assert not Path(queued_path).exists()


def test_load_config_reads_and_validates_environment():
    config = load_config(
        {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_ALLOWED_USER_IDS": "42, 7"}
    )
    assert config == TelegramBotConfig("test-token", frozenset({42, 7}))

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        load_config({"TELEGRAM_ALLOWED_USER_IDS": "42"})
    with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_USER_IDS"):
        load_config({"TELEGRAM_BOT_TOKEN": "test-token"})
    with pytest.raises(ValueError, match="numeric"):
        load_config(
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
                "TELEGRAM_ALLOWED_USER_IDS": "not-a-number",
            }
        )


def test_main_suppresses_http_request_logs_before_polling(monkeypatch):
    config = TelegramBotConfig("secret-token", frozenset({42}))
    application = SimpleNamespace(run_polling=Mock())
    observed = {}

    monkeypatch.setattr("crm.telegram_bot.load_config", lambda: config)

    def fake_create_application(received_config):
        observed["httpx_level"] = logging.getLogger("httpx").getEffectiveLevel()
        return application

    monkeypatch.setattr("crm.telegram_bot.create_application", fake_create_application)
    logging.getLogger("httpx").setLevel(logging.INFO)

    main()

    assert observed["httpx_level"] >= logging.WARNING
    application.run_polling.assert_called_once_with()
