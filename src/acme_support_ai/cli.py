from __future__ import annotations

import argparse

from .orchestrator import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the ACME support assistant.")
    parser.add_argument("question", help="User question")
    args = parser.parse_args()
    print(answer_question(args.question))


if __name__ == "__main__":
    main()
