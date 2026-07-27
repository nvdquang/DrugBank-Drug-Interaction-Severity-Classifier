"""
seed_knowledge_base.py

Migrates local JSON rule files into MySQL Knowledge Base tables (Tier 2).
Allows expert knowledge to be managed directly in the database without code edits.
"""

from __future__ import annotations

import json
from pathlib import Path
import pymysql
from pymysql.cursors import DictCursor

from config import config

RULES_DIR = Path("rules")


def get_connection():
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=DictCursor,
    )


def init_schema(conn):
    """
    Initialize schema tables and safely add columns to drug_interactions.
    """
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS high_risk_drugs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            drug_name VARCHAR(150) NOT NULL UNIQUE,
            drugbank_id VARCHAR(30) NULL,
            is_nti BOOLEAN DEFAULT FALSE,
            risk_category VARCHAR(100) DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS clinical_outcomes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            canonical_event VARCHAR(150) NOT NULL UNIQUE,
            default_severity ENUM('major', 'moderate', 'minor') NOT NULL,
            organ_system VARCHAR(100) DEFAULT 'general',
            description TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS severity_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pattern_type ENUM('pharmacodynamic', 'pharmacokinetic') NOT NULL DEFAULT 'pharmacodynamic',
            raw_term VARCHAR(255) NOT NULL UNIQUE,
            canonical_event VARCHAR(150) NOT NULL,
            base_severity ENUM('major', 'moderate', 'minor') NOT NULL,
            weight FLOAT DEFAULT 1.0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS mechanism_weights (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mechanism_code VARCHAR(50) NOT NULL UNIQUE,
            mechanism_name VARCHAR(100) NOT NULL,
            weight_score FLOAT NOT NULL DEFAULT 1.0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    ]

    alter_cols = [
        ("canonical_event", "VARCHAR(255) NULL AFTER severity"),
        ("pattern", "VARCHAR(30) NULL AFTER canonical_event"),
        ("confidence", "DECIMAL(4,2) NULL AFTER pattern"),
        ("score", "DECIMAL(5,2) NULL AFTER confidence"),
        ("is_high_risk", "BOOLEAN DEFAULT FALSE AFTER score"),
        ("is_nti", "BOOLEAN DEFAULT FALSE AFTER is_high_risk"),
    ]

    with conn.cursor() as cursor:
        for stmt in tables_sql:
            cursor.execute(stmt)

        for col_name, col_def in alter_cols:
            try:
                cursor.execute(f"ALTER TABLE drug_interactions ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

    conn.commit()
    print("[OK] Initialized Knowledge Base Database Schema.")


def seed_clinical_outcomes(conn):
    """
    Seed clinical_outcomes from rules/clinical_events.json
    """
    events_file = RULES_DIR / "clinical_events.json"

    if not events_file.exists():
        return

    events_data = json.loads(events_file.read_text(encoding="utf-8"))

    sql = """
        INSERT INTO clinical_outcomes (canonical_event, default_severity, organ_system)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            default_severity = VALUES(default_severity),
            organ_system = VALUES(organ_system);
    """

    data_to_insert = []
    for severity, categories in events_data.items():
        if not isinstance(categories, dict):
            continue
        for organ_system, events in categories.items():
            if not isinstance(events, list):
                continue
            for event in events:
                event_name = event.strip().lower()
                if not event_name:
                    continue

                data_to_insert.append((event_name, severity, organ_system))

    with conn.cursor() as cursor:
        cursor.executemany(sql, data_to_insert)
    conn.commit()
    print(f"[OK] Seeded {len(data_to_insert)} clinical outcomes into Knowledge Base.")


def seed_high_risk_drugs(conn):
    """
    Seed high_risk_drugs from rules/high_risk_drugs.json
    """
    high_risk_file = RULES_DIR / "high_risk_drugs.json"
    if not high_risk_file.exists():
        return

    data = json.loads(high_risk_file.read_text(encoding="utf-8"))

    sql = """
        INSERT INTO high_risk_drugs (drug_name, is_nti, risk_category)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            is_nti = VALUES(is_nti),
            risk_category = VALUES(risk_category);
    """

    items = []
    for drug in data.get("nti_drugs", []):
        items.append((drug.strip().lower(), True, "Narrow Therapeutic Index"))

    for drug_cls in data.get("high_risk_classes", []):
        items.append((drug_cls.strip().lower(), False, "High Risk Class"))

    with conn.cursor() as cursor:
        cursor.executemany(sql, items)
    conn.commit()
    print(f"[OK] Seeded {len(items)} high-risk drugs & classes into Knowledge Base.")


def seed_severity_rules(conn):
    """
    Seed severity_rules (synonyms and patterns) from rules/synonyms.json
    """
    synonyms_file = RULES_DIR / "synonyms.json"
    events_file = RULES_DIR / "clinical_events.json"

    if not synonyms_file.exists():
        return

    synonyms_data = json.loads(synonyms_file.read_text(encoding="utf-8"))
    events_data = json.loads(events_file.read_text(encoding="utf-8")) if events_file.exists() else {}

    event_severity_map = {}
    for severity, categories in events_data.items():
        if isinstance(categories, dict):
            for _, events in categories.items():
                if isinstance(events, list):
                    for ev in events:
                        event_severity_map[ev.lower().strip()] = severity

    sql = """
        INSERT INTO severity_rules (pattern_type, raw_term, canonical_event, base_severity, weight)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            canonical_event = VALUES(canonical_event),
            base_severity = VALUES(base_severity);
    """

    items = []
    for raw_term, canonical_event in synonyms_data.items():
        raw_term_clean = raw_term.strip().lower()
        canonical_clean = canonical_event.strip().lower()
        if not raw_term_clean or not canonical_clean:
            continue

        base_sev = event_severity_map.get(canonical_clean, "moderate")
        items.append(("pharmacodynamic", raw_term_clean, canonical_clean, base_sev, 1.0))

    with conn.cursor() as cursor:
        cursor.executemany(sql, items)
    conn.commit()
    print(f"[OK] Seeded {len(items)} synonym rules into Knowledge Base.")


def seed_mechanism_weights(conn):
    """
    Seed mechanism_weights table
    """
    mechanisms = [
        ("PD_RISK", "Pharmacodynamic Synergism / Risk Increase", 1.2),
        ("PD_EFFICACY", "Pharmacodynamic Antagonism / Efficacy Decrease", 1.0),
        ("PK_CYP_INH", "Pharmacokinetic CYP Enzyme Inhibition", 1.1),
        ("PK_CYP_IND", "Pharmacokinetic CYP Enzyme Induction", 1.0),
        ("PK_ABS", "Pharmacokinetic Absorption Modification", 0.9),
        ("PK_EXC", "Pharmacokinetic Renal Excretion Modification", 1.0),
    ]

    sql = """
        INSERT INTO mechanism_weights (mechanism_code, mechanism_name, weight_score)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            mechanism_name = VALUES(mechanism_name),
            weight_score = VALUES(weight_score);
    """

    with conn.cursor() as cursor:
        cursor.executemany(sql, mechanisms)
    conn.commit()
    print(f"[OK] Seeded {len(mechanisms)} mechanism weights into Knowledge Base.")


def main():
    print("\n[Knowledge Base Migration] Seeding local rules into MySQL Database...")
    try:
        conn = get_connection()
        init_schema(conn)
        seed_clinical_outcomes(conn)
        seed_high_risk_drugs(conn)
        seed_severity_rules(conn)
        seed_mechanism_weights(conn)
        conn.close()
        print("\n[SUCCESS] Knowledge Base migration completed successfully!")
    except Exception as err:
        print(f"\n[ERROR] Migration failed: {err}")


if __name__ == "__main__":
    main()
