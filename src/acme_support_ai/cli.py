from __future__ import annotations

import argparse
import sys

from .orchestrator import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the ACME support assistant.")
    parser.add_argument("question", help="User question")
    args = parser.parse_args()
    try:
        print(answer_question(args.question))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
