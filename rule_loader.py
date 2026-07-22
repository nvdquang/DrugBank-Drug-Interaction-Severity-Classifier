"""
rule_loader.py

Load and compile rule files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Pattern


RULE_FOLDER = Path("rules")


class RuleLoader:
    """
    Load severity rules from JSON files.
    """

    FILES = (
        "major.json",
        "moderate.json",
        "minor.json",
    )

    def load(self) -> list[tuple[str, Pattern[str]]]:
        """
        Load and compile all rule files.

        Returns
        -------
        list[(severity, compiled_regex)]
        """

        compiled: list[tuple[str, Pattern[str]]] = []

        for filename in self.FILES:

            path = RULE_FOLDER / filename

            if not path.exists():
                raise FileNotFoundError(path)

            with path.open(
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            severity = data["severity"]

            patterns = data["patterns"]

            regex = re.compile(
                "|".join(
                    f"(?:{pattern})"
                    for pattern in patterns
                ),
                re.IGNORECASE,
            )

            compiled.append(
                (
                    severity,
                    regex,
                )
            )

        return compiled