-- ============================================================================
-- DrugBank Drug Interaction Severity Classifier - Knowledge Base Schema (Tier 2)
-- Database: cdss
-- ============================================================================

-- 1. Table: high_risk_drugs (Narrow Therapeutic Index & High Risk Category Drugs)
CREATE TABLE IF NOT EXISTS high_risk_drugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drug_name VARCHAR(150) NOT NULL UNIQUE,
    drugbank_id VARCHAR(30) NULL,
    is_nti BOOLEAN DEFAULT FALSE,
    risk_category VARCHAR(100) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Table: clinical_outcomes (Canonical Clinical Events)
CREATE TABLE IF NOT EXISTS clinical_outcomes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    canonical_event VARCHAR(150) NOT NULL UNIQUE,
    default_severity ENUM('major', 'moderate', 'minor') NOT NULL,
    organ_system VARCHAR(100) DEFAULT 'general',
    description TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Table: severity_rules (Synonyms and Event Keyword Patterns)
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

-- 4. Table: mechanism_weights (Mechanism Scoring Weights)
CREATE TABLE IF NOT EXISTS mechanism_weights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mechanism_code VARCHAR(50) NOT NULL UNIQUE,
    mechanism_name VARCHAR(100) NOT NULL,
    weight_score FLOAT NOT NULL DEFAULT 1.0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Add columns to drug_interactions table for Tier 1/2 outputs
ALTER TABLE drug_interactions
    ADD COLUMN IF NOT EXISTS canonical_event VARCHAR(255) NULL AFTER severity,
    ADD COLUMN IF NOT EXISTS pattern VARCHAR(30) NULL AFTER canonical_event,
    ADD COLUMN IF NOT EXISTS confidence DECIMAL(4,2) NULL AFTER pattern,
    ADD COLUMN IF NOT EXISTS score DECIMAL(5,2) NULL AFTER confidence,
    ADD COLUMN IF NOT EXISTS is_high_risk BOOLEAN DEFAULT FALSE AFTER score,
    ADD COLUMN IF NOT EXISTS is_nti BOOLEAN DEFAULT FALSE AFTER is_high_risk;
