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

    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Offset index to start reading records from.",
    )

    parser.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="Minimum record ID to process.",
    )

    parser.add_argument(
        "--end-id",
        type=int,
        default=None,
        help="Maximum record ID to process.",
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
        offset=args.offset,
        start_id=args.start_id,
        end_id=args.end_id,
    )


if __name__ == "__main__":
    main()