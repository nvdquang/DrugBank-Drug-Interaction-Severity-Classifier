"""
normalizer.py

DrugBank Event Normalizer V5
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RULE_DIR = Path("rules")
SYNONYM_FILE = RULE_DIR / "synonyms.json"


class EventNormalizer:
    """
    Normalize extracted DrugBank clinical events.

    Pipeline

        lower()

            ↓

        remove punctuation

            ↓

        normalize whitespace

            ↓

        remove activity suffix

            ↓

        lookup synonym

            ↓

        canonical event
    """

    def __init__(self):

        self.synonyms = {}

        self._load_synonyms()

        # load known canonical events for heuristic mapping/splitting
        try:
            rule_file = RULE_DIR / 'clinical_events.json'
            if rule_file.exists():
                with rule_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                self.known_events = set()
                for sev, cats in data.items():
                    if isinstance(cats, dict):
                        for cat, events in cats.items():
                            if isinstance(events, list):
                                for e in events:
                                    self.known_events.add(e.lower().strip())
            else:
                self.known_events = set()
        except Exception:
            self.known_events = set()

    # ==========================================================
    # Load Synonyms
    # ==========================================================

    def _load_synonyms(self):

        if not SYNONYM_FILE.exists():

            self.synonyms = {}

            return

        with SYNONYM_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        self.synonyms = {

            k.lower().strip(): v.lower().strip()

            for k, v in data.items()

        }

    # ==========================================================
    # Normalize
    # ==========================================================

    def normalize(
        self,
        event: str,
    ) -> str:

        if not event:

            return ""

        # ------------------------------------------
        # lower
        # ------------------------------------------

        event = event.lower()

        # ------------------------------------------
        # remove/normalize punctuation and delimiters
        # - replace parens, slashes and hyphens with spaces so variants normalize
        # ------------------------------------------

        event = re.sub(r"[\(\)\[\]\{\}/]", " ", event)

        # normalize common separators like hyphen to space (but keep intra-word hyphen handled)
        event = event.replace('-', ' ')

        # remove other punctuation characters
        event = re.sub(r"[.,;:]", "", event)

        # ------------------------------------------
        # normalize whitespace
        # ------------------------------------------

        event = re.sub(r"\s+", " ", event).strip()

        # ------------------------------------------
        # collapse obvious duplicate consecutive words
        # e.g., "depressant depressant" -> "depressant"
        # ------------------------------------------

        event = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", event)

        # ------------------------------------------
        # if the string contains both a long form and an abbreviation
        # like "central nervous system depressant cns depressant",
        # prefer the long form by removing known abbreviations in parentheses or inline
        # (handled by synonyms where possible). Keep this simple: remove short all-caps tokens
        # of length <=4 which often are abbreviations.
        # ------------------------------------------

        tokens = event.split()
        tokens = [t for t in tokens if not (t.isupper() and len(t) <= 4)]
        event = ' '.join(tokens)

        # ------------------------------------------
        # normalize whitespace again
        # ------------------------------------------

        event = re.sub(r"\s+", " ", event).strip()

        # ------------------------------------------
        # remove common suffix
        # ------------------------------------------

        suffixes = (

            " activities",

            " activity",

        )

        for suffix in suffixes:

            if event.endswith(suffix):

                event = event[:-len(suffix)]

                break

        # ------------------------------------------
        # normalize whitespace again
        # ------------------------------------------

        event = re.sub(

            r"\s+",

            " ",

            event,

        ).strip()

        # ------------------------------------------
        # synonym lookup
        # ------------------------------------------

        event = self.synonyms.get(

            event,

            event,

        )

        # ------------------------------------------
        # Morphological heuristics: transform common adjectival suffixes to noun forms
        # e.g., hypoglycemic -> hypoglycemia, arrhythmogenic -> arrhythmia (if applicable),
        # emic -> emia, ic -> ia
        # ------------------------------------------

        if event not in self.known_events:
            # emic -> emia
            cand = re.sub(r'emic\b', 'emia', event)
            if cand in self.known_events:
                return cand
            # ive -> ion (e.g., myelosuppressive -> myelosuppression, immunosuppressive -> immunosuppression, hypotensive -> hypotension)
            cand = re.sub(r'ive\b', 'ion', event)
            if cand in self.known_events:
                return cand
            # genic -> ia (e.g., arrhythmogenic -> arrhythmia)
            cand = re.sub(r'genic\b', 'ia', event)
            if cand in self.known_events:
                return cand
            # toxic -> toxicity (e.g., neurotoxic -> neurotoxicity, cardiotoxic -> cardiotoxicity)
            cand = re.sub(r'toxic\b', 'toxicity', event)
            if cand in self.known_events:
                return cand
            # cardic -> cardia (e.g., bradycardic -> bradycardia, tachycardic -> tachycardia)
            cand = re.sub(r'cardic\b', 'cardia', event)
            if cand in self.known_events:
                return cand
            # antihypertensive -> hypotension
            if event == 'antihypertensive':
                return 'hypotension'
            # ic -> ia (simple heuristic)
            cand = re.sub(r'ic\b', 'ia', event)
            if cand in self.known_events:
                return cand
            # other small heuristics
            cand = re.sub(r'tic\b', 'tics', event)
            if cand in self.known_events:
                return cand

        # ------------------------------------------
        # If still not a known canonical and contains conjunctions/commas,
        # try splitting and return first subpart that maps to known events or synonyms.
        # This helps with strings like "x and y" or "a and b and c".
        # ------------------------------------------

        if event not in self.known_events:
            # split on common separators
            parts = re.split(r"\band\b|,|/|\\&| and |;", event)
            parts = [p.strip() for p in parts if p.strip()]
            for p in parts:
                # try synonyms first
                s = self.synonyms.get(p, p)
                if s in self.known_events:
                    return s
                # fallback: if the raw part itself is known
                if p in self.known_events:
                    return p
            # if none matched, return the original event

        return event

    # ==========================================================
    # Reload
    # ==========================================================

    def reload(self):

        self._load_synonyms()

    # ==========================================================
    # Statistics
    # ==========================================================

    @property
    def synonym_count(self):

        return len(self.synonyms)