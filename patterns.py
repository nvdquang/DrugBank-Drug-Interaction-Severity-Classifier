"""
patterns.py

DrugBank Pattern Engine V5
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ==========================================================
# Pattern Types
# ==========================================================

PD = "pharmacodynamic"
PK = "pharmacokinetic"
OTHER = "other"

PK_PATTERN_TYPES = {PK}

# ==========================================================
# Result
# ==========================================================


@dataclass(slots=True)
class PatternResult:

    pattern_type: str

    event: str

    direction: str

    confidence: float


# ==========================================================
# Pattern Matcher
# ==========================================================


class PatternMatcher:

    def __init__(self):

        self.patterns = [

            # ======================================================
            # PD
            # ======================================================

            (
                PD,
                re.compile(
                    r"The risk or severity of (.+?) (?:can be|is) (increased|decreased)",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    r"The risk of (.+?) (?:can be|is) (increased|decreased)",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    r"may (increase|decrease) the (.+?) activities of",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    r"may (increase|decrease) the (.+?) of",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    r"The therapeutic efficacy of .+? can be (increased|decreased)",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    r".+? may (increase|decrease) effectiveness of .+?",
                    re.IGNORECASE,
                ),
            ),

            (
                PD,
                re.compile(
                    # Capture the direction (increase/decrease) so extraction can rely on a group
                    r".+? can cause an? (decrease|increase) in the absorption of .+? resulting in .*? (?:decrease|increase|worsening)",
                    re.IGNORECASE,
                ),
            ),

            # ======================================================
            # PK
            # ======================================================

            (
                PK,
                re.compile(
                    r"The metabolism of (?:the active metabolites? of )?.+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The serum concentration of (?:the active metabolites? of )?.+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The plasma concentration of (?:the active metabolites? of )?.+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The blood concentration of (?:the active metabolites? of )?.+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The bioavailability of .+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The absorption of .+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The excretion (?:rate )?of .+? can be (increased|decreased)",
                    re.IGNORECASE,
                ),
            ),

            (
                PK,
                re.compile(
                    r"The protein binding of .+? can be (increased|decreased|reduced)",
                    re.IGNORECASE,
                ),
            ),

        ]

    # ==========================================================
    # Extract
    # ==========================================================

    def extract(
        self,
        description: str,
    ) -> Optional[PatternResult]:

        if not description:
            return None

        for pattern_type, regex in self.patterns:

            m = regex.search(description)

            if not m:
                continue

            # ==================================================
            # Pharmacodynamic
            # ==================================================

            if pattern_type == PD:

                if len(m.groups()) == 2:

                    # risk pattern

                    if "risk" in regex.pattern.lower():

                        event = m.group(1)

                        direction = m.group(2)

                    else:

                        direction = m.group(1)

                        event = m.group(2)

                else:

                    event = "therapeutic efficacy"

                    # Some PD patterns only capture the direction (increase/decrease),
                    # and a few patterns capture nothing. Safely infer the direction
                    # from the match text or the full description when no group is present.
                    if len(m.groups()) >= 1 and m.group(1):
                        # Normalize group value to consistent past-tense form
                        d = m.group(1).lower()
                        if d in ("decrease", "decreased", "reduced"):
                            direction = "decreased"
                        elif d in ("increase", "increased"):
                            direction = "increased"
                        else:
                            direction = d
                    else:
                        txt = (m.group(0) or description).lower()
                        if "decrease" in txt:
                            direction = "decreased"
                        elif "increase" in txt:
                            direction = "increased"
                        else:
                            direction = "unknown"

                return PatternResult(

                    pattern_type=PD,

                    event=event.strip(),

                    direction=direction.lower(),

                    confidence=1.0,

                )

            # ==================================================
            # Pharmacokinetic
            # ==================================================

            text = description.lower()

            if "metabolism" in text:
                event = "metabolism"

            elif "serum concentration" in text:
                event = "serum concentration"

            elif "plasma concentration" in text:
                event = "plasma concentration"

            elif "blood concentration" in text:
                event = "blood concentration"

            elif "bioavailability" in text:
                event = "bioavailability"

            elif "protein binding" in text:
                event = "protein binding"

            elif "absorption" in text:
                event = "absorption"

            elif "excretion" in text:
                event = "excretion"

            else:
                event = "pharmacokinetics"

            direction = m.group(1).lower() if len(m.groups()) >= 1 else "increased"
            if direction in ("reduced", "decrease"):
                direction = "decreased"

            return PatternResult(

                pattern_type=PK,

                event=event,

                direction=direction,

                confidence=1.0,

            )

        return None