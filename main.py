"""
main.py

Drug Interaction Severity Classification
"""

from __future__ import annotations

import argparse

from runner import Runner


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Drug Interaction Severity Classifier"
    )

    parser.add_argument(
        "limit",
        nargs="?",
        type=int,
        default=None,
        help="Number of records to process (default: process all records).",
    )

    return parser.parse_args()


def main() -> None:
    """
    Program entry point.
    """

    args = parse_args()

    runner = Runner()

    runner.run(
        limit=args.limit,
    )


if __name__ == "__main__":
    main()