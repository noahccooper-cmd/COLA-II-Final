-- COLA II - DuckDB Schema for Persistent Multi-Document Intelligence
-- Creates data gravity through document and finding storage with benchmark calculations

-- ============================================================================
-- DOCUMENTS TABLE - Every PDF ever uploaded
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR PRIMARY KEY,
    filename VARCHAR NOT NULL,
    upload_date TIMESTAMP NOT NULL,
    file_hash VARCHAR UNIQUE NOT NULL,
    plan_name VARCHAR,
    plan_size_bucket VARCHAR CHECK (plan_size_bucket IN ('<100', '100-500', '500-1000', '1000+', 'unknown')),
    provider_hash VARCHAR,
    document_type VARCHAR CHECK (document_type IN ('408b2', '404a5', '5500', 'other')),
    page_count INTEGER,
    processing_status VARCHAR CHECK (processing_status IN ('processing', 'completed', 'failed')),
    processing_time_seconds FLOAT,
    total_findings INTEGER DEFAULT 0,
    risk_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- NEW FIELDS FOR PRODUCTION POLISH
    client_tag VARCHAR,
    is_benchmark_eligible BOOLEAN DEFAULT TRUE,
    plan_size_category VARCHAR,
    plan_industry VARCHAR
);

-- ============================================================================
-- FINDINGS TABLE - Every violation ever detected
-- ============================================================================
CREATE TABLE IF NOT EXISTS findings (
    finding_id VARCHAR PRIMARY KEY,
    doc_id VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    subtype VARCHAR NOT NULL,
    decision VARCHAR NOT NULL CHECK (decision IN ('present', 'absent', 'suspected', 'unclear')),
    severity VARCHAR NOT NULL CHECK (severity IN ('prohibited_transaction', 'critical', 'high', 'medium', 'low')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    red_flag_score INTEGER DEFAULT 0,
    lawsuit_precedent TEXT,
    legal_citation TEXT,
    llm_analysis TEXT,
    citations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ruleset_version VARCHAR NOT NULL,
    model_version VARCHAR NOT NULL,
    -- NEW FIELDS FOR PRODUCTION POLISH
    reviewed_by_user BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR,
    dedup_group_id VARCHAR,
    instance_count INTEGER DEFAULT 1
);

-- ============================================================================
-- BENCHMARK STATISTICS - Aggregate intelligence that creates data gravity
-- ============================================================================
CREATE TABLE IF NOT EXISTS benchmark_stats (
    stat_id VARCHAR PRIMARY KEY,
    plan_size_bucket VARCHAR,
    category VARCHAR NOT NULL,
    subtype VARCHAR,
    avg_red_flag_score FLOAT,
    median_confidence FLOAT,
    violation_frequency FLOAT,
    sample_size INTEGER NOT NULL,
    percentile_25 FLOAT,
    percentile_50 FLOAT,
    percentile_75 FLOAT,
    percentile_90 FLOAT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_findings_doc_id ON findings(doc_id);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_benchmark_category ON benchmark_stats(category);
CREATE INDEX IF NOT EXISTS idx_benchmark_bucket ON benchmark_stats(plan_size_bucket);

-- ============================================================================
-- INITIAL STATISTICS VIEW
-- ============================================================================
CREATE OR REPLACE VIEW document_summary AS
SELECT
    COUNT(*) as total_documents,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed_documents,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_documents,
    AVG(total_findings) as avg_findings_per_doc,
    AVG(risk_score) as avg_risk_score,
    AVG(processing_time_seconds) as avg_processing_time
FROM documents;

CREATE OR REPLACE VIEW category_summary AS
SELECT
    category,
    COUNT(*) as total_occurrences,
    AVG(red_flag_score) as avg_red_flag,
    COUNT(DISTINCT doc_id) as docs_with_category,
    (COUNT(DISTINCT doc_id)::FLOAT / (SELECT COUNT(*) FROM documents WHERE processing_status = 'completed')::FLOAT) * 100 as category_frequency_pct
FROM findings
WHERE decision = 'present'
GROUP BY category
ORDER BY total_occurrences DESC;
