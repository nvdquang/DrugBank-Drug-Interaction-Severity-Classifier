# DrugBank Drug Interaction Severity Classifier

A high-performance, rule-based NLP pipeline designed to classify the severity of DrugBank drug-drug interactions (DDIs) based on textual interaction descriptions and synchronize classification results directly into a MySQL database.

---

## 🌟 Key Features

* **Multi-stage NLP Classification Pipeline**:
  * **Pattern Extraction (`patterns.py`)**: Regular expression engine detecting **Pharmacodynamic (PD)** and **Pharmacokinetic (PK)** interaction mechanisms.
  * **Event Normalization (`normalizer.py`)**: Case normalization, punctuation handling, abbreviation cleanup, adjectival-to-noun morphological transformation, conjunction splitting, and synonym mapping.
  * **Severity Assignment (`classifier.py`)**: Mapping canonical events to severity levels (**Major**, **Moderate**, **Minor**) with confidence scoring (1.0 for exact match, 0.90 for partial match).
* **High Performance & Streaming I/O**:
  * Memory-efficient streaming reads from MySQL via `SSDictCursor`.
  * Batch database updates using `executemany()` via `DictCursor`.
  * Precompiled regular expressions and cached lookup tables.
* **Continuous Rule Refinement Toolchain**:
  * Exports unmapped/unknown interactions to `logs/unknown_events.csv`.
  * Automated tools for analyzing unknown events, proposing token-overlap synonym mappings, and simulating rule impact.
* **Zero Machine Learning Overhead**: Deterministic, scalable, transparent, and reproducible.

---

## 🏗️ Pipeline Architecture

```
                    ┌───────────────────────────────┐
                    │      MySQL Database           │
                    │   (drug_interactions table)   │
                    └──────────────┬────────────────┘
                                   │  Streaming Read (SSDictCursor)
                                   ▼
                    ┌───────────────────────────────┐
                    │       Pattern Matcher         │
                    │    (PD / PK Extraction)       │
                    └──────────────┬────────────────┘
                                   │ Extracted Event & Pattern Type
                                   ▼
                    ┌───────────────────────────────┐
                    │       Event Normalizer        │
                    │ (Synonyms, Morph, Split)      │
                    └──────────────┬────────────────┘
                                   │ Canonical Event
                                   ▼
                    ┌───────────────────────────────┐
                    │      Severity Classifier      │
                    │ (clinical_events.json Lookup) │
                    └──────────────┬────────────────┘
                                   │ SeverityResult (Major/Moderate/Minor/Unknown)
                                   ▼
                    ┌───────────────────────────────┐
                    │     Batch MySQL Database      │
                    │     Update (executemany)      │
                    └──────────────┬────────────────┘
                                   │
                                   ▼
                    ┌───────────────────────────────┐
                    │ Export Unknown Interactions   │
                    │  (logs/unknown_events.csv)    │
                    └───────────────────────────────┘
```

---

## 📁 Project Structure

```
DrugBank_Drug_Severity/
│
├── config.py                   # Application & MySQL database credentials
├── database.py                 # MySQL access layer (streaming read & batch update)
├── models.py                   # Dataclasses (Interaction, SeverityResult, UnknownEvent, Statistics)
├── patterns.py                 # PatternMatcher engine V5 (Regex extraction for PD & PK)
├── normalizer.py               # EventNormalizer V5 (Text cleaning, synonyms & heuristics)
├── rule_loader.py              # Rule loader helper for individual severity JSON files
├── classifier.py               # SeverityClassifier production engine V3
├── runner.py                   # Batch execution pipeline & progress display
├── main.py                     # CLI entry point
│
├── analyze_unknowns.py         # Utility: Analyze unknown events & export top unmapped candidates
├── auto_map_unmapped.py        # Utility: Heuristic auto-mapping of unmapped events to synonyms.json
├── simulate_synonym_effect.py  # Utility: Simulate resolution improvement using new synonyms
├── count_minor.py              # Utility: Frequency counter for minor interaction keywords
├── find_min_ids.py             # Utility: Id helper script
├── test_patterns.py            # Unit tests for PatternMatcher
│
├── rules/
│   ├── clinical_events.json    # Canonical clinical events grouped by severity & organ system
│   ├── synonyms.json           # Raw-to-canonical event synonym dictionary
│   ├── major.json              # Specific patterns for major severity
│   ├── moderate.json           # Specific patterns for moderate severity
│   └── minor.json              # Specific patterns for minor severity
│
├── logs/                       # Auto-generated CSV reports (e.g. unknown_events.csv)
│
├── requirements.txt            # Dependency specification
└── README.md                   # Project documentation
```

---

## ⚙️ Requirements & Installation

* **Python**: 3.10 or higher
* **MySQL**: 8.0 or higher
* **Dependencies**: `pymysql`

Install requirements:

```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Setup & Schema

The application reads from and updates the target database specified in `config.py` (default: `cdss`).

### Table Name
`drug_interactions`

### Required Columns

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `INT` (Primary Key) | Interaction record identifier |
| `description` | `TEXT` | Raw text description of the drug interaction |
| `severity` | `VARCHAR` | Output severity (`major`, `moderate`, `minor`, `unknown`) |
| `canonical_event` | `VARCHAR` | Normalized canonical clinical event (e.g., `bleeding`, `arrhythmia`) |
| `pattern` | `VARCHAR` | Interaction mechanism (`pharmacodynamic`, `pharmacokinetic`) |
| `confidence` | `FLOAT` | Classification confidence score (`1.0` exact match, `0.9` partial) |

### SQL ADD COLUMN
| ALTER TABLE drug_interactions
| ADD COLUMN canonical_event VARCHAR(255) NULL AFTER severity,
| ADD COLUMN pattern VARCHAR(30) NULL AFTER canonical_event,
| ADD COLUMN confidence DECIMAL(4,2) NULL AFTER pattern;
---

## 🔧 Configuration

Edit database connection details and batch sizes in `config.py`:

```python
@dataclass(frozen=True, slots=True)
class Config:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "YOUR_PASSWORD"
    database: str = "YOUR_DATABASE"
    fetch_size: int = 5000
    update_batch_size: int = 5000
```

---

## 🚀 Usage

### 1. Standard Full Processing
Process all records in the database:
```bash
python main.py
```

### 2. Sample Batch Processing
Process the first 1,000 records for testing:
```bash
python main.py 1000
```

### 3. Chunked Processing Strategies (For Large Datasets ~3 Million Records)

For processing large datasets in multi-pass chunks (e.g., 3 passes of 1,000,000 records each):

#### Option A: Offset-based Chunking (`limit` & `--offset`)
```bash
# Pass 1: First 1,000,000 records
python main.py 1000000 --offset 0

# Pass 2: Second 1,000,000 records
python main.py 1000000 --offset 1000000

# Pass 3: Remaining records
python main.py 1000000 --offset 2000000
```

#### Option B: ID Range Chunking (`--start-id` & `--end-id`) *(Fastest MySQL Query)*
```bash
# Pass 1: ID range 1 to 1,000,000
python main.py --start-id 1 --end-id 1000000

# Pass 2: ID range 1,000,001 to 2,000,000
python main.py --start-id 1000001 --end-id 2000000

# Pass 3: ID range 2,000,001 to 3,000,000
python main.py --start-id 2000001 --end-id 3000000
```

### 4. Run Unit Tests
```bash
python -m unittest test_patterns.py
```

---

## 📊 Continuous Rule Optimization Workflow

When running `main.py`, records that cannot be mapped to a known clinical event are logged into `logs/unknown_events.csv`. Follow this workflow to analyze and expand the knowledge base:

1. **Analyze Unknown Events**:
   ```bash
   python analyze_unknowns.py
   ```
   *Generates `logs/top_unmapped.csv` listing the most frequent unmapped canonical events.*

2. **Auto-propose & Append Synonyms**:
   ```bash
   python auto_map_unmapped.py
   ```
   *Applies token-overlap heuristics to automatically append mappings to `rules/synonyms.json`.*

3. **Simulate Optimization Impact**:
   ```bash
   python simulate_synonym_effect.py
   ```
   *Simulates the improvement in classification resolution rate before running a full database update.*

---

## 📚 Rule File Specifications

### 1. `rules/clinical_events.json`
Categorizes canonical clinical events by severity level and medical taxonomy:

```json
{
  "major": {
    "hematologic": [
      "bleeding",
      "hemorrhage",
      "thrombosis"
    ],
    "cardiovascular": [
      "arrhythmia",
      "qt prolongation"
    ]
  },
  "moderate": { ... },
  "minor": { ... }
}
```

### 2. `rules/synonyms.json`
Maps extracted event variants and phrases to their canonical forms:

```json
{
  "increased risk of bleeding": "bleeding",
  "hypoglycemic": "hypoglycemia",
  "central nervous system depression": "cns depression"
}
```

---

## 👤 Author

**M.Sc. Nguyen Vu Duy Quang**  
Faculty of Information Technology  
Lac Hong University (LHU) — [lhu.edu.vn](https://lhu.edu.vn)  
Vietnam
