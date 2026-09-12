import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from crm.telegram_bot import (
    DOWNLOAD_ERROR_MESSAGE,
    GENERIC_ERROR_MESSAGE,
    GROUP_MESSAGE,
    HELP_MESSAGE,
    MISSING_CAPTION_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    UNSUPPORTED_MESSAGE,
    TelegramBotConfig,
    build_handlers,
    load_config,
    main,
)


class FakeAttachment:
    def __init__(self, content: bytes = b"image", *, download_error=None):
        self.content = content
        self.download_error = download_error

    async def get_file(self):
        attachment = self

        class File:
            async def download_to_drive(self, custom_path):
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
    media_group_id=None,
):
    message = SimpleNamespace(
        caption=caption,
        photo=photo or [],
        document=document,
        text=text,
        media_group_id=media_group_id,
        reply_text=AsyncMock(),
    )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(type=chat_type),
        effective_message=message,
    )


def run(coro):
    return asyncio.run(coro)


def test_photo_maps_to_graph_while_file_exists_then_cleans_up():
    seen = {}

    class Graph:
        def invoke(self, state):
            seen.update(state)
            seen["exists_during_invoke"] = Path(state["image_path"]).is_file()
            return {**state, "status": "complete", "errors": []}

    update = make_update(photo=[FakeAttachment(b"card")], caption="  Ada Lovelace  ")
    handlers = build_handlers({42}, Graph())

    run(handlers.intake(update, None))

    assert seen == {
        "name": "Ada Lovelace",
        "image_path": seen["image_path"],
        "voice_path": None,
        "status": "pending",
        "errors": [],
        "exists_during_invoke": True,
    }
    assert not Path(seen["image_path"]).exists()
    update.effective_message.reply_text.assert_awaited_once_with(
        "✓ Input accepted\n\nName: Ada Lovelace\nStatus: complete"
    )


@pytest.mark.parametrize(
    ("mime_type", "file_name"),
    [("image/jpeg", "card.jpg"), ("image/png", "card.png")],
)
def test_supported_image_document_maps_to_graph(mime_type, file_name):
    graph = Mock()
    graph.invoke.return_value = {
        "name": "Ada Lovelace",
        "status": "complete",
        "errors": [],
    }
    document = FakeAttachment()
    document.mime_type = mime_type
    document.file_name = file_name
    update = make_update(document=document)

    run(build_handlers({42}, graph).intake(update, None))

    assert graph.invoke.call_args.args[0]["image_path"].endswith(
        ".png" if mime_type == "image/png" else ".jpg"
    )


def test_missing_caption_is_rejected_without_graph_call():
    graph = Mock()
    update = make_update(photo=[FakeAttachment()], caption="  ")

    run(build_handlers({42}, graph).intake(update, None))

    graph.invoke.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once_with(
        MISSING_CAPTION_MESSAGE
    )


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


def test_graph_rejection_does_not_expose_file_path():
    class Graph:
        def invoke(self, state):
            return {
                **state,
                "status": "invalid",
                "errors": [f"image file not found: {state['image_path']}"],
            }

    update = make_update(photo=[FakeAttachment()])

    run(build_handlers({42}, Graph()).intake(update, None))

    reply = update.effective_message.reply_text.await_args.args[0]
    assert reply.startswith("✗ Input rejected\n\n")
    assert "/tmp" not in reply and "/var" not in reply
    assert "image" in reply.lower()


def test_unexpected_graph_exception_is_generic():
    seen = {}

    class Graph:
        def invoke(self, state):
            seen.update(state)
            raise ValueError("secret internal detail")

    update = make_update(photo=[FakeAttachment()])

    run(build_handlers({42}, Graph()).intake(update, None))

    update.effective_message.reply_text.assert_awaited_once_with(GENERIC_ERROR_MESSAGE)
    assert not Path(seen["image_path"]).exists()


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
