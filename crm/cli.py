import argparse
import json
import sys

from dotenv import load_dotenv

from crm.graph import build_graph


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="crm")
    parser.add_argument("--name", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--voice", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parse_args(argv)
    graph = build_graph()
    result = graph.invoke(
        {
            "name": args.name,
            "image_path": args.image,
            "voice_path": args.voice,
            "status": "pending",
            "errors": [],
            "contact_evidence": None,
            "extracted_card": None,
            "voice_transcript": None,
            "conversation_notes": None,
        }
    )
    payload = {
        "name": result.get("name"),
        "image_path": result.get("image_path"),
        "voice_path": result.get("voice_path"),
        "status": result.get("status"),
        "errors": result.get("errors", []),
        "contact_evidence": result.get("contact_evidence"),
        "voice_transcript": result.get("voice_transcript"),
        "conversation_notes": result.get("conversation_notes"),
    }
    print(json.dumps(payload, indent=2))
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
