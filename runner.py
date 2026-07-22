"""
runner.py

Production Runner v1.0
"""

from __future__ import annotations

import csv
import time
from collections import Counter
from pathlib import Path

from classifier import SeverityClassifier
from database import Database
from models import SeverityResult


class Runner:
    """
    Execute DrugBank Severity Classification.
    """

    def __init__(self) -> None:

        self.db = Database()

        self.classifier = SeverityClassifier()

        # Store unknown interactions
        self.unknown_events: list[dict] = []

    # =====================================================
    # Main
    # =====================================================

    def run(
        self,
        limit: int | None = None,
    ) -> None:

        start_time = time.time()

        processed = 0

        updated = 0

        unknown = 0

        severity_stats = Counter()

        try:

            # ==========================================
            # Load interactions by batch
            # ==========================================

            for interactions in self.db.load_interactions(limit):

                # --------------------------------------
                # Classify current batch
                # --------------------------------------

                results = self.classifier.classify_batch(
                    interactions
                )

                valid_results: list[SeverityResult] = []

                # --------------------------------------
                # Collect valid / unknown
                # --------------------------------------

                for interaction, result in zip(
                    interactions,
                    results,
            ):
                    # --------------------------------------
                    # Unknown
                    # --------------------------------------

                    if result is None or result.severity == "unknown":
                        unknown += 1
                        self.unknown_events.append(
                            {
                                "id": interaction.id,
                                "description": interaction.description,
                                "pattern": result.pattern if result else "",
                                "event": result.event if result else "",
                                "canonical_event": result.canonical_event if result else "",
                            }
                        )
                        continue

                    # --------------------------------------
                    # Valid Result
                    # --------------------------------------

                    valid_results.append(result)
                    severity_stats[result.severity] += 1

                # --------------------------------------
                # Update database
                # --------------------------------------

                if valid_results:
                    valid_results = [
                        r
                        for r in valid_results
                        if r.severity != "unknown"
                    ]
                    self.db.update_batch(valid_results)
                    updated += len(valid_results)

                processed += len(interactions)

                # --------------------------------------
                # Progress
                # --------------------------------------

                elapsed = time.time() - start_time

                speed = processed / elapsed if elapsed > 0 else 0

                print(
                    f"\rProcessed: {processed:,}"
                    f" | Updated: {updated:,}"
                    f" | Unknown: {unknown:,}"
                    f" | Speed: {speed:,.0f} rows/sec",
                    end="",
                    flush=True,
                )
        finally:
            self.db.close()

        # ==========================================
        # Export unknown interactions
        # ==========================================

        self.export_unknown_events()

        elapsed = time.time() - start_time

        success_rate = (
            (updated / processed) * 100
            if processed > 0
            else 0
        )

        unknown_rate = (
            (unknown / processed) * 100
            if processed > 0
            else 0
        )

        print()

        print("=" * 70)
        print("Drug Interaction Severity Classification Completed")
        print("=" * 70)

        print(f"Processed : {processed:,}")
        print(f"Updated   : {updated:,}")
        print(f"Unknown   : {unknown:,}")

        print()

        print(
            f"Success Rate : {success_rate:.2f}%"
        )

        print(
            f"Unknown Rate : {unknown_rate:.2f}%"
        )

        print()

        print("Severity Summary")

        print("-" * 70)

        for severity in (

            "major",

            "moderate",

            "minor",

        ):

            print(

                f"{severity:<12}"

                f"{severity_stats[severity]:>12,}"

            )

        print("-" * 70)

        print(
            f"Elapsed Time : {elapsed:.2f} seconds"
        )

        if elapsed > 0:

            print(

                f"Average Speed: "

                f"{processed / elapsed:,.0f} rows/sec"

            )

        print("=" * 70)
    
        # =====================================================
    # Export Unknown Interactions
    # =====================================================

    def export_unknown_events(self) -> None:
        """
        Export unknown interactions to CSV for
        future rule improvements.
        """

        if not self.unknown_events:
            return

        log_dir = Path("logs")

        log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        csv_file = log_dir / "unknown_events.csv"

        try:

            with csv_file.open(
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "id",
                        "description",
                        "pattern",
                        "event",
                        "canonical_event",
                    ],
                )

                writer.writeheader()

                writer.writerows(
                    self.unknown_events
                )

            print()

            print(
                f"Unknown interactions exported:"
            )

            print(
                f"{csv_file}"
            )

            print(
                f"Total Unknown : "
                f"{len(self.unknown_events):,}"
            )

        except Exception as ex:

            print()

            print(
                "WARNING: Unable to export "
                "unknown_events.csv"
            )

            print(ex)