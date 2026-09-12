import argparse
import json
import sys

from dotenv import load_dotenv

from crm.db import DEFAULT_DB_PATH, ContactStore
from crm.graph import build_graph
from crm.providers.embeddings import GroqEmbedder
from crm.search import query_contacts
from crm.tracing import enable_tracing


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="crm")
    parser.add_argument("--name", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--notes", default=None)
    sub = parser.add_subparsers(dest="command")
    query = sub.add_parser("query")
    query.add_argument("text")
    query.add_argument("--limit", type=int, default=5)
    return parser.parse_args(argv)


def _format_query_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matches."
    blocks = []
    for i, hit in enumerate(hits, 1):
        lines = [f"{i}. {hit.get('full_name') or 'Unknown'}"]
        for key in ("company", "job_title"):
            value = hit.get(key)
            if value and str(value).strip():
                lines.append(f"   {value}")
        notes = hit.get("notes")
        if notes and str(notes).strip():
            lines.append("")
            for line in str(notes).splitlines():
                lines.append(f"   {line}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _run_query(args: argparse.Namespace, embedder=None, store=None) -> int:
    active_embedder = embedder if embedder is not None else GroqEmbedder.from_env()
    active_store = (
        store
        if store is not None
        else ContactStore(DEFAULT_DB_PATH, embedding_dim=active_embedder.dimension)
    )
    hits = query_contacts(active_store, active_embedder, args.text, args.limit)
    print(_format_query_hits(hits))
    return 0


def main(argv: list[str] | None = None, *, embedder=None, store=None) -> int:
    load_dotenv()
    enable_tracing()
    args = _parse_args(argv)
    if args.command == "query":
        return _run_query(args, embedder=embedder, store=store)
    graph = build_graph()
    result = graph.invoke(
        {
            "name": args.name,
            "image_path": args.image,
            "voice_path": args.voice,
            "typed_notes": args.notes,
            "status": "pending",
            "errors": [],
            "contact_evidence": None,
            "extracted_card": None,
            "voice_transcript": None,
            "conversation_notes": None,
            "normalized_contact": None,
            "matched_contact_id": None,
            "contact_id": None,
            "crm_action": None,
            "verified_contact": None,
        }
    )
    payload = {
        "name": result.get("name"),
        "image_path": result.get("image_path"),
        "voice_path": result.get("voice_path"),
        "typed_notes": result.get("typed_notes"),
        "status": result.get("status"),
        "errors": result.get("errors", []),
        "contact_evidence": result.get("contact_evidence"),
        "voice_transcript": result.get("voice_transcript"),
        "conversation_notes": result.get("conversation_notes"),
        "contact_id": result.get("contact_id"),
        "crm_action": result.get("crm_action"),
        "verified_contact": result.get("verified_contact"),
    }
    print(json.dumps(payload, indent=2))
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
