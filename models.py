"""
models.py

Data models for DrugBank Severity Classification.
"""

from __future__ import annotations

from dataclasses import dataclass


# ==========================================================
# Drug Interaction
# ==========================================================

@dataclass(slots=True)
class Interaction:
    """
    Drug interaction record.
    """

    id: int

    description: str


# ==========================================================
# Severity Result
# ==========================================================

@dataclass(slots=True)
class SeverityResult:
    """
    Classification result.
    """

    # Database ID

    id: int

    # major / moderate / minor

    severity: str

    # Raw event extracted by PatternMatcher

    event: str = ""

    # Canonical event after normalization

    canonical_event: str = ""

    # pharmacodynamic / pharmacokinetic

    pattern: str = ""

    # Classification confidence

    confidence: float = 1.0


# ==========================================================
# Unknown Event
# ==========================================================

@dataclass(slots=True)
class UnknownEvent:
    """
    Unknown event for logging.
    """

    id: int

    description: str

    extracted_event: str

    canonical_event: str

    pattern: str


# ==========================================================
# Statistics
# ==========================================================

@dataclass(slots=True)
class Statistics:

    processed: int = 0

    updated: int = 0

    unknown: int = 0

    major: int = 0

    moderate: int = 0

    minor: int = 0

    pharmacodynamic: int = 0

    pharmacokinetic: int = 0

    average_confidence: float = 0.0