import argparse
import json
import sys

from crm.graph import build_graph


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="crm")
    parser.add_argument("--name", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--voice", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    graph = build_graph()
    result = graph.invoke(
        {
            "name": args.name,
            "image_path": args.image,
            "voice_path": args.voice,
            "status": "pending",
            "errors": [],
        }
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
