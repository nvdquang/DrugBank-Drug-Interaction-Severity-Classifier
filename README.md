# DrugBank Drug Interaction Severity Classifier (Tier 1 & Tier 2)
### Hệ thống phân loại mức độ nghiêm trọng tương tác thuốc DrugBank

A high-performance, rule-based NLP & Dynamic Knowledge Base system designed to classify the severity of DrugBank drug-drug interactions (DDIs) based on textual interaction descriptions and synchronize classification results directly into a MySQL database.

*Hệ thống phân loại mức độ nghiêm trọng của tương tác thuốc (DDIs) hiệu năng cao dựa trên quy tắc xử lý ngôn ngữ tự nhiên (NLP) và Cơ sở tri thức động (MySQL). Tự động trích xuất cơ chế, chuẩn hóa biến cố lâm sàng, tính điểm chỉ số nguy cơ (NTI/High-Risk) và đồng bộ trực tiếp kết quả phân loại vào cơ sở dữ liệu.*

---

## 🌟 Key Features / Tính năng nổi bật

* **Hybrid Architecture (Tier 1 Rule Engine & Tier 2 Knowledge Base)** / *Kiến trúc Lai*:
  * **Pattern Extraction (`patterns.py`)** / *Trích xuất Mô hình*: Regular expression engine detecting **Pharmacodynamic (PD)** and **Pharmacokinetic (PK)** interaction mechanisms. (*Động cơ Regex trích xuất cơ chế Dược lực học và Dược động học.*)
  * **Event Normalizer (`normalizer.py`)** / *Chuẩn hóa Biến cố*: Case normalization, punctuation handling, abbreviation cleanup, morphological transformation, conjunction splitting, and synonym mapping. (*Xử lý chữ hoa/thường, dấu câu, viết tắt, hình thái học, tách liên từ và từ đồng nghĩa.*)
  * **Dynamic Knowledge Base Loader (`db_rule_loader.py`)** / *Bộ nạp Tri thức Động*: Loads rules directly from MySQL (`clinical_outcomes`, `severity_rules`, `high_risk_drugs`, `mechanism_weights`) into RAM with zero latency, falling back to local JSON files if DB connection is unavailable. (*Nạp quy tắc từ MySQL vào RAM với độ trễ 0ms, fallback về JSON nếu mất kết nối DB.*)
  * **Risk Scoring & Evaluation (`classifier.py`)** / *Đánh giá Rủi ro*:
    * Flags Narrow Therapeutic Index (**NTI**) drugs (e.g., Warfarin, Digoxin, Lithium). (*Nhận diện thuốc có khoảng điều trị hẹp.*)
    * Flags **High-Risk** drug classes and combinations. (*Nhận diện nhóm thuốc nguy cơ cao.*)
    * **Dynamic Scoring Engine**: Computes rule scores and assigns severity levels (**Major**, **Moderate**, **Minor**, **Unknown**). (*Động cơ tính điểm động và gắn mức độ nghiêm trọng.*)

* **High Performance & Streaming I/O** / *Tối ưu Hiệu năng & I/O Luồng*:
  * Memory-efficient streaming reads from MySQL via `SSDictCursor`. (*Đọc luồng tiết kiệm bộ nhớ.*)
  * Batch updates using `executemany()` via `DictCursor`. (*Cập nhật hàng loạt hiệu năng cao.*)
  * Precompiled regular expressions and cached lookup tables. (*Regex biên dịch sẵn và từ điển lưu tạm.*)

* **Continuous Rule Refinement Toolchain** / *Công cụ Tối ưu Quy tắc Liên tục*:
  * Exports unmapped/unknown interactions to `logs/unknown_events.csv`. (*Xuất các tương tác chưa khớp.*)
  * Automated tools to analyze unmapped events, propose synonyms, and simulate resolution improvements. (*Công cụ phân tích, gợi ý ánh xạ tự động và mô phỏng hiệu quả.*)

---

## 🏗️ Pipeline Architecture / Kiến trúc Hệ thống

```
                    ┌───────────────────────────────┐
                    │      MySQL Database           │
                    │   (drug_interactions table)   │
                    └──────────────┬────────────────┘
                                   │ Streaming Read (SSDictCursor)
                                   ▼
                    ┌───────────────────────────────┐
                    │       Pattern Matcher         │
                    │    (PD / PK Extraction)       │
                    └──────────────┬────────────────┘
                                   │ Raw Event & Pattern Type
                                   ▼
                    ┌───────────────────────────────┐
                    │       Event Normalizer        │
                    │ (Synonyms, Morph, Splitting)  │
                    └──────────────┬────────────────┘
                                   │ Canonical Event
                                   ▼
                    ┌───────────────────────────────┐
                    │   Knowledge Base Loader DB    │
                    │  (MySQL Cache / JSON Fallback)│
                    └──────────────┬────────────────┘
                                   │ Event Severity, NTI & Risk Weights
                                   ▼
                    ┌───────────────────────────────┐
                    │      Severity Classifier      │
                    │ (Dynamic Scoring & Weighting) │
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

## 📁 Project Structure / Cấu trúc Thư mục

```
DrugBank_Drug_Severity/
│
├── config.py                   # App configuration & MySQL database credentials / Cấu hình kết nối MySQL
├── database.py                 # MySQL access layer (Streaming read & batch update) / Lớp truy xuất MySQL
├── models.py                   # Dataclasses (Interaction, SeverityResult, UnknownEvent, Statistics)
├── patterns.py                 # Regex extraction engine for PD & PK / Trích xuất Regex cơ chế PD & PK
├── normalizer.py               # Text cleaning, morphological rules & synonyms / Chuẩn hóa từ vựng & đồng nghĩa
├── db_rule_loader.py           # Dynamic Knowledge Base loader / Bộ nạp tri thức động từ MySQL
├── classifier.py               # Production severity classifier engine / Bộ phân loại mức độ nghiêm trọng
├── runner.py                   # Batch pipeline runner & progress bar / Luồng xử lý hàng loạt
├── main.py                     # Main CLI entry point / CLI điều khiển chính
├── seed_knowledge_base.py      # Schema init & seeding script / Script khởi tạo & nạp tri thức vào DB
├── schema_tier2.sql            # Knowledge Base SQL Schema (Tier 2) / Schema SQL cho Knowledge Base
│
├── analyze_unknowns.py         # Utility: Analyze unknown events / Phân tích biến cố chưa ánh xạ
├── auto_map_unmapped.py        # Utility: Auto-propose synonym mappings / Gợi ý tự động ánh xạ đồng nghĩa
├── simulate_synonym_effect.py  # Utility: Simulate resolution improvement / Mô phỏng tỷ lệ cải thiện
├── count_minor.py              # Utility: Frequency counter for minor keywords / Thống kê từ khóa minor
├── find_min_ids.py             # Utility: ID helper script / Helper tìm ID
│
├── test_patterns.py            # Unit tests: PatternMatcher
├── test_tier1_engine.py        # Unit tests: Tier 1 Rule Engine
├── test_tier2_kb.py            # Unit tests: Tier 2 Knowledge Base
├── test_unknown_resolution.py  # Unit tests: Unknown resolution
│
├── rules/                      # Fallback JSON rule files / Tệp quy tắc JSON fallback
│   ├── clinical_events.json    # Canonical clinical events / Biến cố lâm sàng chuẩn hóa
│   ├── synonyms.json           # Raw-to-canonical synonyms / Từ điển đồng nghĩa
│   ├── high_risk_drugs.json    # NTI drugs & high-risk classes / Danh sách thuốc NTI & nguy cơ cao
│   ├── major.json              # Major severity patterns / Mẫu quy tắc mức Major
│   ├── moderate.json           # Moderate severity patterns / Mẫu quy tắc mức Moderate
│   └── minor.json              # Minor severity patterns / Mẫu quy tắc mức Minor
│
├── logs/                       # Auto-generated CSV reports / Báo cáo CSV tự động
├── requirements.txt            # Dependency specification / Thư viện phụ thuộc
└── README.md                   # Project documentation / Tài liệu hướng dẫn
```

---

## ⚙️ Requirements & Installation / Yêu cầu & Cài đặt

* **Python**: 3.10+
* **MySQL**: 8.0+
* **Dependencies / Thư viện**: `pymysql`

Install dependencies / *Cài đặt thư viện*:

```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Setup & Schema / Cấu trúc Cơ sở Dữ liệu

### 1. Main Output Table / Bảng lưu kết quả: `drug_interactions`

Output column specifications / *Chi tiết các cột kết quả*:

| Column / Cột | Type / Kiểu | Description / Mô tả |
| :--- | :--- | :--- |
| `id` | `INT` (PK) | Interaction identifier / Mã định danh tương tác |
| `description` | `TEXT` | Raw DDI text description / Mô tả tương tác thuốc |
| `severity` | `VARCHAR` | Output severity (`major`, `moderate`, `minor`, `unknown`) |
| `canonical_event` | `VARCHAR` | Normalized canonical clinical event / Biến cố lâm sàng chuẩn hóa |
| `pattern` | `VARCHAR` | Interaction mechanism (`pharmacodynamic`, `pharmacokinetic`) |
| `confidence` | `DECIMAL(4,2)` | Classification confidence score (1.0 exact, 0.9 partial) |
| `score` | `DECIMAL(5,2)` | Combined Rule Engine score / Điểm đánh giá tổng hợp |
| `is_high_risk` | `BOOLEAN` | High-risk drug/combination flag / Cờ đánh dấu nhóm nguy cơ cao |
| `is_nti` | `BOOLEAN` | Narrow Therapeutic Index flag / Cờ đánh dấu thuốc chỉ số trị liệu hẹp |

#### SQL Add Columns Statement / *Câu lệnh SQL thêm cột*:
```sql
ALTER TABLE drug_interactions
    ADD COLUMN IF NOT EXISTS canonical_event VARCHAR(255) NULL AFTER severity,
    ADD COLUMN IF NOT EXISTS pattern VARCHAR(30) NULL AFTER canonical_event,
    ADD COLUMN IF NOT EXISTS confidence DECIMAL(4,2) NULL AFTER pattern,
    ADD COLUMN IF NOT EXISTS score DECIMAL(5,2) NULL AFTER confidence,
    ADD COLUMN IF NOT EXISTS is_high_risk BOOLEAN DEFAULT FALSE AFTER score,
    ADD COLUMN IF NOT EXISTS is_nti BOOLEAN DEFAULT FALSE AFTER is_high_risk;
```

### 2. Tier 2 Knowledge Base Tables / Các bảng Cơ sở tri thức:
Run `schema_tier2.sql` or `python seed_knowledge_base.py` to create / *Chạy tệp SQL hoặc script python để khởi tạo*:
1. **`high_risk_drugs`**: NTI drugs & high-risk categories. (*Danh sách thuốc NTI & phân loại nguy cơ cao.*)
2. **`clinical_outcomes`**: Canonical clinical events & default severity levels. (*Biến cố lâm sàng & mức độ mặc định.*)
3. **`severity_rules`**: Raw-term to canonical event synonym mapping rules. (*Quy tắc ánh xạ từ đồng nghĩa.*)
4. **`mechanism_weights`**: Mechanism scoring weights. (*Trọng số scoring theo cơ chế.*)

---

## 🔧 Configuration / Cấu hình

Edit connection details in `config.py` / *Chỉnh sửa thông tin kết nối MySQL trong `config.py`*:

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

## 🚀 Usage Instructions / Hướng dẫn Sử dụng

### 1. Initialize Knowledge Base / Khởi tạo Cơ sở Tri thức
Seed Knowledge Base tables into MySQL / *Nạp dữ liệu quy tắc vào MySQL*:
```bash
python seed_knowledge_base.py
```

### 2. Full Processing / Phân loại Toàn bộ
Process all records in the database / *Phân loại toàn bộ bản ghi trong DB*:
```bash
python main.py
```

### 3. Sample Processing / Phân loại Thử nghiệm
Process the first 1,000 records / *Thử nghiệm 1.000 bản ghi đầu tiên*:
```bash
python main.py 1000
```

### 4. Chunked Processing Strategies / Phân đoạn tập dữ liệu lớn (~3 Triệu bản ghi)

#### Option A: ID Range Chunking (`--start-id` & `--end-id`) *(Recommended / Tối ưu nhất)*
```bash
# Chunk 1: ID 1 to 1,000,000
python main.py --start-id 1 --end-id 1000000

# Chunk 2: ID 1,000,001 to 2,000,000
python main.py --start-id 1000001 --end-id 2000000

# Chunk 3: ID 2,000,001 to 3,000,000
python main.py --start-id 2000001 --end-id 3000000
```

#### Option B: Offset Chunking (`limit` & `--offset`)
```bash
# Chunk 1: First 1,000,000 records
python main.py 1000000 --offset 0

# Chunk 2: Next 1,000,000 records
python main.py 1000000 --offset 1000000
```

### 5. Reprocess Unknown Records Only / Phân loại lại các bản ghi Chưa xác định
Re-process only records where `severity` is currently `unknown`, `NULL`, or empty / *Chỉ xử lý bản ghi chưa xác định*:
```bash
python main.py --only-unknown
```

### 6. Run Unit Tests / Chạy Bộ Kiểm thử
```bash
python -m unittest discover -p "test_*.py"
```

---

## 📊 Continuous Rule Optimization / Quy trình Tối ưu Quy tắc

1. **Analyze Unknown Events / Phân tích bản ghi Unknown**:
   ```bash
   python analyze_unknowns.py
   ```
   *Generates `logs/top_unmapped.csv` listing top unmapped events. (Tạo báo cáo top các biến cố chưa khớp).*

2. **Auto-propose Synonyms / Gợi ý tự động từ đồng nghĩa**:
   ```bash
   python auto_map_unmapped.py
   ```
   *Applies heuristics to suggest and append mappings to `rules/synonyms.json`. (Gợi ý và thêm vào tệp synonyms.json).*

3. **Simulate Impact / Mô phỏng hiệu quả**:
   ```bash
   python simulate_synonym_effect.py
   ```
   *Evaluates classification resolution improvement before full DB update. (Đánh giá tỷ lệ cải thiện trước khi chạy DB).*

---

## 👤 Author / Tác giả

** M.Sc. Nguyen Vu Duy Quang **  
Email: quang@lhu.edu.vn  
Faculty of Information Technology / Khoa Công nghệ Thông tin  
Lac Hong University (LHU) — [lhu.edu.vn](https://lhu.edu.vn)  
Vietnam
