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
from db_rule_loader import DBRuleLoader


RULE_FILE = Path("rules") / "clinical_events.json"
HIGH_RISK_FILE = Path("rules") / "high_risk_drugs.json"


class SeverityClassifier:
    """
    Production Rule-based Severity Classifier (Tier 1 & 2 Hybrid Knowledge Base).

    Pipeline

    Description
        ↓
    Pattern Matcher
        ↓
    Event Normalizer & Knowledge Base (MySQL / RAM Cache)
        ↓
    Rule Engine Scoring & Severity Lookup
        ↓
    SeverityResult (with score, NTI flag)
    """

    def __init__(self, use_db_kb: bool = True):

        self.matcher = PatternMatcher()

        self.normalizer = EventNormalizer()

        # canonical_event -> severity

        self.event_lookup: dict[str, str] = {}

        # High-risk & NTI rules
        self.nti_drugs: list[str] = []
        self.high_risk_classes: list[str] = []
        self.high_risk_events: list[str] = []

        # Knowledge Base loader
        self.kb = DBRuleLoader()

        if use_db_kb:
            self._load_from_knowledge_base()
        else:
            self._load_rules()
            self._load_high_risk_rules()

    def _load_from_knowledge_base(self) -> None:
        """
        Load rules dynamically from MySQL Knowledge Base (or JSON fallback).
        """
        self.kb.load()
        if self.kb.event_lookup:
            self.event_lookup = self.kb.event_lookup
        else:
            self._load_rules()

        if self.kb.nti_drugs:
            self.nti_drugs = self.kb.nti_drugs
            self.high_risk_classes = self.kb.high_risk_classes
            if self.kb.high_risk_events:
                self.high_risk_events = self.kb.high_risk_events
            else:
                self._load_high_risk_rules()
        else:
            self._load_high_risk_rules()

        if self.kb.synonyms:
            self.normalizer.synonyms.update(self.kb.synonyms)


    # ==========================================================
    # Load High-Risk Rules
    # ==========================================================

    def _load_high_risk_rules(self) -> None:
        """
        Load high_risk_drugs.json
        """
        if not HIGH_RISK_FILE.exists():
            # Fallback default rules
            self.nti_drugs = ["warfarin", "digoxin", "lithium", "theophylline", "tacrolimus", "cyclosporine", "phenytoin", "carbamazepine"]
            self.high_risk_classes = ["anticoagulant", "antiplatelet", "antiarrhythmic", "immunosuppressant", "opioid", "nsaid"]
            self.high_risk_events = ["bleeding", "hemorrhage", "arrhythmia", "qt prolongation", "torsades de pointes", "respiratory depression"]
            return

        with HIGH_RISK_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.nti_drugs = [d.lower() for d in data.get("nti_drugs", [])]
        self.high_risk_classes = [c.lower() for c in data.get("high_risk_classes", [])]
        self.high_risk_events = [e.lower() for e in data.get("high_risk_events", [])]


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

        # ------------------------------------------
        # Token Overlap & Fuzzy Matcher (Unknown Reduction)
        # ------------------------------------------

        best_severity = None
        best_score = 0.0
        canon_tokens = set(canonical_event.lower().split())

        for keyword, severity in self.event_lookup.items():
            kw_tokens = set(keyword.lower().split())
            if not kw_tokens:
                continue

            intersection = 0.0
            for ct in canon_tokens:
                for kt in kw_tokens:
                    if ct == kt:
                        intersection += 1.0
                    elif len(ct) >= 5 and len(kt) >= 5 and (ct.startswith(kt[:5]) or kt.startswith(ct[:5])):
                        intersection += 0.85

            kw_len = len(kw_tokens)
            overlap_score = intersection / kw_len if kw_len > 0 else 0.0

            if overlap_score > best_score and overlap_score >= 0.70:
                best_score = overlap_score
                best_severity = severity

        if best_severity is not None:
            return best_severity, 0.85

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
    # High-Risk & NTI Evaluation (Tầng 1 Engine)
    # ==========================================================

    def _evaluate_high_risk(
        self,
        description: str,
        canonical_event: str,
    ) -> tuple[bool, bool, list[str]]:
        """
        Evaluate if interaction involves Narrow Therapeutic Index (NTI) drugs,
        High-Risk drug classes, or Critical Clinical Events.

        Returns:
            (is_nti, is_high_risk, risk_factors)
        """
        text = (description or "").lower()
        risk_factors: list[str] = []
        is_nti = False
        is_high_risk = False

        # 1. Check NTI Drugs
        for drug in self.nti_drugs:
            if drug in text:
                is_nti = True
                is_high_risk = True
                risk_factors.append(f"NTI Drug: {drug.capitalize()}")

        # 2. Check High-Risk Drug Classes
        for cls in self.high_risk_classes:
            if cls in text:
                is_high_risk = True
                risk_factors.append(f"High-Risk Class: {cls.capitalize()}")

        # 3. Check High-Risk Clinical Events
        for evt in self.high_risk_events:
            if evt in canonical_event.lower() or (evt in text and not canonical_event):
                is_high_risk = True
                risk_factors.append(f"High-Risk Event: {evt.capitalize()}")

        return is_nti, is_high_risk, risk_factors

    # ==========================================================
    # Dynamic Scoring & Severity Adjustment
    # ==========================================================

    def _calculate_score_and_severity(
        self,
        base_severity: str,
        confidence: float,
        is_nti: bool,
        is_high_risk: bool,
        canonical_event: str,
        pattern_type: str,
    ) -> tuple[float, str, float]:
        """
        Calculates Rule Engine Score S_total and adjusts final severity if needed.

        Returns:
            (score, adjusted_severity, adjusted_confidence)
        """
        severity_scores = {
            "major": 3.0,
            "moderate": 2.0,
            "minor": 1.0,
            "unknown": 0.0,
        }

        score = severity_scores.get(base_severity, 0.0)

        # Apply bonuses
        if is_nti:
            score += 1.5
        elif is_high_risk:
            score += 1.0

        if pattern_type in PK_PATTERN_TYPES and is_nti:
            score += 0.5

        # Weighted by match confidence
        final_score = round(score * confidence, 2)
        adjusted_severity = base_severity
        adjusted_confidence = confidence

        # Severe event or NTI combination upgrade:
        # Upgrade Moderate -> Major if NTI drug is involved with high-risk events (e.g., bleeding, toxicity, arrhythmia)
        if base_severity == "moderate" and is_nti and is_high_risk:
            adjusted_severity = "major"
            adjusted_confidence = max(confidence, 0.95)
        elif final_score >= 3.5 and base_severity != "major" and base_severity != "unknown":
            adjusted_severity = "major"
            adjusted_confidence = max(confidence, 0.90)

        return final_score, adjusted_severity, adjusted_confidence

    def _classify_pk(
        self,
        interaction: Interaction,
        raw_event: str,
        canonical_event: str,
    ) -> SeverityResult:
        """
        Pharmacokinetic interactions classification with High-Risk/NTI scoring.
        """
        is_nti, is_high_risk, risk_factors = self._evaluate_high_risk(
            interaction.description,
            canonical_event,
        )

        score, severity, confidence = self._calculate_score_and_severity(
            base_severity="moderate",
            confidence=1.0,
            is_nti=is_nti,
            is_high_risk=is_high_risk,
            canonical_event=canonical_event,
            pattern_type="pharmacokinetic",
        )

        return SeverityResult(
            id=interaction.id,
            severity=severity,
            event=raw_event,
            canonical_event=canonical_event,
            pattern="pharmacokinetic",
            confidence=confidence,
            score=score,
            is_high_risk=is_high_risk,
            is_nti=is_nti,
            risk_factors=risk_factors,
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

        # No pattern match: Fallback to full-text semantic keyword scanner
        if result is None:
            text = (interaction.description or "").lower()
            # 1. Search synonyms first (prefer longer matches)
            for k in sorted(self.normalizer.synonyms.keys(), key=len, reverse=True):
                if k and k in text:
                    canon = self._canonicalize_event(k)
                    return ("pharmacodynamic", k, canon)

            # 2. Search known canonical event lookup
            for ev in sorted(self.event_lookup.keys(), key=len, reverse=True):
                if ev and ev in text:
                    return ("pharmacodynamic", ev, ev)

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

        is_nti, is_high_risk, risk_factors = self._evaluate_high_risk(
            interaction.description,
            canonical_event,
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
                score=0.0,
                is_high_risk=is_high_risk,
                is_nti=is_nti,
                risk_factors=risk_factors,
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
                score=0.0,
                is_high_risk=is_high_risk,
                is_nti=is_nti,
                risk_factors=risk_factors,
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

                score=0.0,

                is_high_risk=is_high_risk,

                is_nti=is_nti,

                risk_factors=risk_factors,

            )

        # ------------------------------------------
        # Dynamic Scoring
        # ------------------------------------------

        score, adjusted_severity, adjusted_confidence = self._calculate_score_and_severity(
            base_severity=severity,
            confidence=confidence,
            is_nti=is_nti,
            is_high_risk=is_high_risk,
            canonical_event=canonical_event,
            pattern_type="pharmacodynamic",
        )

        # ------------------------------------------
        # Build Result
        # ------------------------------------------

        return SeverityResult(

            id=interaction.id,

            severity=adjusted_severity,

            event=raw_event,

            canonical_event=canonical_event,

            pattern="pharmacodynamic",

            confidence=adjusted_confidence,

            score=score,

            is_high_risk=is_high_risk,

            is_nti=is_nti,

            risk_factors=risk_factors,

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