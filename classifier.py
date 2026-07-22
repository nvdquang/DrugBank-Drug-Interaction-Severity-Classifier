"""
classifier.py

DrugBank Severity Classifier
Production Version 3
"""

from __future__ import annotations

import json
from pathlib import Path

from models import (
    Interaction,
    SeverityResult,
)

from patterns import (
    PatternMatcher,
    PK_PATTERN_TYPES,
)

from normalizer import EventNormalizer


RULE_FILE = Path("rules") / "clinical_events.json"


class SeverityClassifier:
    """
    Production Rule-based Severity Classifier.

    Pipeline

    Description
        ↓
    Pattern Matcher
        ↓
    Event Normalizer
        ↓
    Canonical Event
        ↓
    Severity Lookup
        ↓
    SeverityResult
    """

    def __init__(self):

        self.matcher = PatternMatcher()

        self.normalizer = EventNormalizer()

        # canonical_event -> severity

        self.event_lookup: dict[str, str] = {}

        self._load_rules()

    # ==========================================================
    # Load Clinical Events
    # ==========================================================

    def _load_rules(self) -> None:

        """
        Load clinical_events.json

        Format

        {
            "major": [...],
            "moderate": [...],
            "minor": [...]
        }
        """

        with RULE_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        self.event_lookup.clear()

        for severity, categories in data.items():

            if not isinstance(categories, dict):
                continue

            for _, events in categories.items():

                if not isinstance(events, list):
                    continue

                for event in events:

                    event = event.lower().strip()

                    if not event:
                        continue

                    self.event_lookup[event] = severity

    # ==========================================================
    # Exact / Partial Lookup
    # ==========================================================

    def _lookup_severity(
        self,
        canonical_event: str,
    ) -> tuple[str | None, float]:
        
        assert isinstance(canonical_event, str), (
        type(canonical_event),
        canonical_event,
        )

        """
        Returns

        severity,
        confidence
        """

        if not canonical_event:

            return None, 0.0

        # ------------------------------------------
        # Exact Match
        # ------------------------------------------

        severity = self.event_lookup.get(
            canonical_event
        )

        if severity is not None:

            return severity, 1.0

        # ------------------------------------------
        # Partial Match
        # ------------------------------------------

        for keyword, severity in self.event_lookup.items():

            if keyword in canonical_event:

                return severity, 0.90

            if canonical_event in keyword:

                return severity, 0.90

        return None, 0.0
    
    # ==========================================================
    # Canonical Event
    # ==========================================================

    def _canonicalize_event(
        self,
        event: str,
    ) -> str:
        """
        Normalize extracted event into canonical form.
        """

        if not event:
            return ""

        return self.normalizer.normalize(event)

    # ==========================================================
    # Pharmacokinetic Classification
    # ==========================================================

    def _classify_pk(
        self,
        interaction: Interaction,
        raw_event: str,
        canonical_event: str,
    ) -> SeverityResult:
        """
        All pharmacokinetic interactions are currently classified
        as Moderate.
        """

        return SeverityResult(

            id=interaction.id,

            severity="moderate",

            event=raw_event,

            canonical_event=canonical_event,

            pattern="pharmacokinetic",

            confidence=1.0,

        )

    # ==========================================================
    # Extract Event
    # ==========================================================

    def _extract_event(
        self,
        interaction: Interaction,
    ) -> tuple[str | None, str, str]:

        result = self.matcher.extract(
            interaction.description
        )

        # No pattern match
        if result is None:
            return (
                None,
                "",
                "",
            )

        pattern_type = result.pattern_type
        raw_event = (result.event or "").strip()
        canonical_event = self._canonicalize_event(
            raw_event
        )

        # If extractor returned an empty raw_event, try to heuristically find
        # a known event or synonym in the description text.
        if not raw_event:
            text = (interaction.description or "").lower()

            # Prefer longer synonym keys to match multi-word phrases first
            for k in sorted(self.normalizer.synonyms.keys(), key=len, reverse=True):
                if k and k in text:
                    raw_event = k
                    canonical_event = self._canonicalize_event(k)
                    break

            # If still empty, search known canonical events
            if not raw_event:
                for ev in sorted(self.normalizer.known_events, key=len, reverse=True):
                    if ev and ev in text:
                        raw_event = ev
                        canonical_event = ev
                        break

        return (
            pattern_type,
            raw_event,
            canonical_event,
        )

    # ==========================================================
    # Classify One Interaction
    # ==========================================================

    def classify(
        self,
        interaction: Interaction,
    ) -> SeverityResult | None:

        # ------------------------------------------
        # Extract
        # ------------------------------------------

        (
            pattern_type,
            raw_event,
            canonical_event,
        ) = self._extract_event(
            interaction
        )

        # ------------------------------------------
        # No Pattern Matched
        # ------------------------------------------

        if pattern_type is None:
            return SeverityResult(
                id=interaction.id,
                severity="unknown",
                event="",
                canonical_event="",
                pattern="",
                confidence=0.0,
            )

        # ------------------------------------------
        # Pharmacokinetic
        # ------------------------------------------

        if pattern_type in PK_PATTERN_TYPES:
            return self._classify_pk(
                interaction,
                raw_event,
                canonical_event,
            )
       
        # ------------------------------------------
        # Empty Event
        # ------------------------------------------

        if not canonical_event:

            return SeverityResult(
                id=interaction.id,
                severity="unknown",
                event=raw_event,
                canonical_event="",
                pattern=pattern_type,
                confidence=0.0,
            )

        
        # ------------------------------------------
        # Lookup Severity
        # ------------------------------------------
       
        severity, confidence = self._lookup_severity(

            canonical_event

        )

        # ------------------------------------------
        # Unknown Event
        # ------------------------------------------

        if severity is None:

            return SeverityResult(

                id=interaction.id,

                severity="unknown",

                event=raw_event,

                canonical_event=canonical_event,

                pattern="pharmacodynamic",

                confidence=0.0,

            )

        # ------------------------------------------
        # Build Result
        # ------------------------------------------

        return SeverityResult(

            id=interaction.id,

            severity=severity,

            event=raw_event,

            canonical_event=canonical_event,

            pattern="pharmacodynamic",

            confidence=confidence,

        )
    
    # ==========================================================
    # Batch Classification
    # ==========================================================

    def classify_batch(
        self,
        interactions: list[Interaction],
    ) -> list[SeverityResult | None]:

        results: list[SeverityResult | None] = []

        for interaction in interactions:

            results.append(

                self.classify(
                    interaction
                )

            )

        return results

    # ==========================================================
    # Filter Valid Results
    # ==========================================================

    @staticmethod
    def filter_valid(
        results: list[SeverityResult | None],
    ) -> tuple[list[SeverityResult], int]:

        valid: list[SeverityResult] = []

        unknown = 0

        for result in results:

            if result is None:

                unknown += 1

            else:

                valid.append(result)

        return (

            valid,

            unknown,

        )

    # ==========================================================
    # Statistics Helper
    # ==========================================================

    @staticmethod
    def severity_statistics(
        results: list[SeverityResult],
    ) -> dict[str, int]:

        stats = {

            "major": 0,

            "moderate": 0,

            "minor": 0,

        }

        for result in results:

            severity = result.severity.lower()

            stats.setdefault(

                severity,

                0,

            )

            stats[severity] += 1

        return stats

    # ==========================================================
    # Pattern Statistics
    # ==========================================================

    @staticmethod
    def pattern_statistics(
        results: list[SeverityResult],
    ) -> dict[str, int]:

        stats = {

            "pharmacodynamic": 0,

            "pharmacokinetic": 0,

        }

        for result in results:

            stats.setdefault(

                result.pattern,

                0,

            )

            stats[result.pattern] += 1

        return stats

    # ==========================================================
    # Average Confidence
    # ==========================================================

    @staticmethod
    def average_confidence(
        results: list[SeverityResult],
    ) -> float:

        if not results:

            return 0.0

        return (

            sum(

                r.confidence

                for r in results

            )

            / len(results)

        )