"""
db_rule_loader.py

Dynamic Knowledge Base Loader (Tier 2).
Loads rules directly from MySQL database tables into memory with zero-latency lookups.
Falls back seamlessly to local JSON rule files if database is unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import pymysql
from pymysql.cursors import DictCursor

from config import config

RULES_DIR = Path("rules")


class DBRuleLoader:
    """
    Tier 2 Dynamic Knowledge Base Loader.
    """

    def __init__(self) -> None:
        self.event_lookup: dict[str, str] = {}
        self.synonyms: dict[str, str] = {}
        self.nti_drugs: list[str] = []
        self.high_risk_classes: list[str] = []
        self.high_risk_events: list[str] = []
        self.mechanism_weights: dict[str, float] = {}

        self.loaded_from_db: bool = False

    def load(self) -> None:
        """
        Attempt to load from MySQL database first; fallback to local JSON files.
        """
        if self._load_from_db():
            self.loaded_from_db = True
            print("[INFO] [Knowledge Base] Rules successfully loaded dynamically from MySQL Database.")
        else:
            self._load_from_json()
            self.loaded_from_db = False
            print("[INFO] [Knowledge Base] Loaded fallback rules from local JSON files.")

    def _get_db_connection(self):
        try:
            return pymysql.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                charset="utf8mb4",
                autocommit=True,
                cursorclass=DictCursor,
                connect_timeout=3,
            )
        except Exception:
            return None

    def _load_from_db(self) -> bool:
        conn = self._get_db_connection()
        if conn is None:
            return False

        try:
            with conn.cursor() as cursor:
                # 1. Load Clinical Outcomes
                cursor.execute("SELECT canonical_event, default_severity FROM clinical_outcomes")
                outcomes = cursor.fetchall()
                if not outcomes:
                    conn.close()
                    return False

                self.event_lookup.clear()
                for row in outcomes:
                    ev = row["canonical_event"].lower().strip()
                    sev = row["default_severity"].lower().strip()
                    self.event_lookup[ev] = sev

                # 2. Load High-Risk & NTI Drugs
                cursor.execute("SELECT drug_name, is_nti, risk_category FROM high_risk_drugs")
                drugs = cursor.fetchall()
                self.nti_drugs.clear()
                self.high_risk_classes.clear()
                for row in drugs:
                    name = row["drug_name"].lower().strip()
                    if row.get("is_nti"):
                        self.nti_drugs.append(name)
                    else:
                        self.high_risk_classes.append(name)

                # 3. Load Severity Rules (Synonyms)
                cursor.execute("SELECT raw_term, canonical_event FROM severity_rules WHERE is_active = TRUE")
                syn_rows = cursor.fetchall()
                self.synonyms.clear()
                for row in syn_rows:
                    self.synonyms[row["raw_term"].lower().strip()] = row["canonical_event"].lower().strip()

                # 4. Load Mechanism Weights
                cursor.execute("SELECT mechanism_code, weight_score FROM mechanism_weights")
                m_rows = cursor.fetchall()
                self.mechanism_weights.clear()
                for row in m_rows:
                    self.mechanism_weights[row["mechanism_code"]] = float(row["weight_score"])

            conn.close()
            return True
        except Exception as e:
            print(f"[Knowledge Base Warning] DB load error: {e}")
            if conn:
                conn.close()
            return False

    def _load_from_json(self) -> None:
        """
        Fallback JSON loader
        """
        # Load clinical_events.json
        events_file = RULES_DIR / "clinical_events.json"
        if events_file.exists():
            data = json.loads(events_file.read_text(encoding="utf-8"))
            self.event_lookup.clear()
            for severity, categories in data.items():
                if isinstance(categories, dict):
                    for _, events in categories.items():
                        if isinstance(events, list):
                            for ev in events:
                                self.event_lookup[ev.lower().strip()] = severity

        # Load synonyms.json
        syn_file = RULES_DIR / "synonyms.json"
        if syn_file.exists():
            data = json.loads(syn_file.read_text(encoding="utf-8"))
            self.synonyms = {k.lower().strip(): v.lower().strip() for k, v in data.items()}

        # Load high_risk_drugs.json
        hr_file = RULES_DIR / "high_risk_drugs.json"
        if hr_file.exists():
            data = json.loads(hr_file.read_text(encoding="utf-8"))
            self.nti_drugs = [d.lower() for d in data.get("nti_drugs", [])]
            self.high_risk_classes = [c.lower() for c in data.get("high_risk_classes", [])]
            self.high_risk_events = [e.lower() for e in data.get("high_risk_events", [])]
