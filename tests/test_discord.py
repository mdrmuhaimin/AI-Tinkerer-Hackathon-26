from crm.db import ContactStore
from crm.discord_bot import Intake
from crm.graph import build_graph
from tests.helpers import FakeEmbedder, FakeExtractor, FakeTranscriber
from tests.test_crm import SARAH, _count, _run, _touch
from tests.test_embeddings import DECOY, DECOY_NOTES, RELATED_QUERY, WORKFLOW_NOTES


def _intake(tmp_path, *, graph=None, store=None, extractor=None, transcriber=None):
    store = store or ContactStore(tmp_path / "crm.db", embedding_dim=8)
    embedder = FakeEmbedder()
    extractor = extractor or FakeExtractor(SARAH)
    transcriber = transcriber or FakeTranscriber()
    if graph is None:

        def graph():
            return build_graph(
                extractor=extractor,
                transcriber=transcriber,
                store=store,
                embedder=embedder,
            )

    return (
        Intake(
            download=lambda path: path,
            build_graph=graph,
            store=store,
            embedder=embedder,
        ),
        store,
        extractor,
        transcriber,
    )


def test_image_and_name_stays_pending_without_persist(tmp_path) -> None:
    created: list[object] = []

    def boom():
        raise AssertionError("build_graph")

    intake, store, _, _ = _intake(tmp_path, graph=boom)
    orig = store.create
    store.create = lambda *a, **k: created.append(1) or orig(*a, **k)
    image = _touch(tmp_path / "card.jpg")

    reply = intake.handle_dm(
        "42",
        "Sarah Khan\nMet at a booth.",
        [image],
        [],
    )

    assert reply is not None
    assert "save" in reply.lower()
    assert "42" in intake.pending
    assert created == []
    assert _count(store) == 0


def test_follow_up_voice_runs_graph_and_stores_notes(tmp_path) -> None:
    transcriber = FakeTranscriber("Discussed a CRM pilot.")
    intake, store, extractor, _ = _intake(tmp_path, transcriber=transcriber)
    image = _touch(tmp_path / "card.jpg")
    voice = _touch(tmp_path / "note.ogg")

    intake.handle_dm("7", "Sarah Khan\nPotential lead.", [image], [])
    reply = intake.handle_dm("7", "", [], [voice])

    assert "7" not in intake.pending
    assert "Sarah Khan" in reply
    assert "NexaTech Solutions" in reply
    assert "created" in reply
    assert "contact_id=" in reply
    assert extractor.calls == [image]
    assert transcriber.calls == [voice]
    row = store.get(1)
    assert row is not None
    assert "Potential lead." in (row["notes"] or "")
    assert "Discussed a CRM pilot." in (row["notes"] or "")


def test_save_without_voice_skips_transcriber(tmp_path) -> None:
    transcriber = FakeTranscriber("should not run")
    intake, store, _, _ = _intake(tmp_path, transcriber=transcriber)
    image = _touch(tmp_path / "card.jpg")

    intake.handle_dm("9", "Sarah Khan", [image], [])
    reply = intake.handle_dm("9", "SAVE", [], [])

    assert transcriber.calls == []
    assert "9" not in intake.pending
    assert "created" in reply
    assert store.get(1) is not None


def test_query_ranks_contact_and_never_calls_graph(tmp_path) -> None:
    first, store = _run(tmp_path, SARAH, transcript=WORKFLOW_NOTES)
    _run(tmp_path, DECOY, transcript=DECOY_NOTES, store=store)
    before = _count(store)

    def boom():
        raise AssertionError("build_graph")

    intake, _, _, _ = _intake(tmp_path, graph=boom, store=store)
    ranked = intake.handle_query(RELATED_QUERY)
    slashed = intake.handle_dm("3", f"/query {RELATED_QUERY}", [], [])

    assert "Sarah Khan" in ranked
    assert "Sarah Khan" in slashed
    assert _count(store) == before
    assert store.get(first["contact_id"])["full_name"] == "Sarah Khan"


def test_guild_channel_messages_ignored(tmp_path) -> None:
    def boom():
        raise AssertionError("build_graph")

    intake, store, _, _ = _intake(tmp_path, graph=boom)
    image = _touch(tmp_path / "card.jpg")

    reply = intake.handle_message(
        "99",
        "Sarah Khan",
        [image],
        [],
        is_dm=False,
    )

    assert reply is None
    assert intake.pending == {}
    assert _count(store) == 0
