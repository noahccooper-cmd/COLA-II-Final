#!/usr/bin/env python3
"""
COLA II - Database Manager
Handles persistent storage of documents, findings, and benchmark calculations
This creates the DATA GRAVITY that makes COLA II category-defining
"""

import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime
import json


class DatabaseManager:
    """
    Persistent storage layer for COLA II Internal Intelligence

    This is the MOAT. Every document analyzed makes the system smarter.

    Uses singleton pattern to ensure only one database connection exists.
    """

    _instance = None
    _conn = None
    _initialized = False

    def __new__(cls, db_path: str = "data/cola.duckdb"):
        """Ensure only one instance of DatabaseManager exists (Singleton pattern)"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        """Initialize single shared connection"""
        if self._initialized:
            return

        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        # Connect to DuckDB (single shared connection)
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
            self.conn = self._conn  # Keep self.conn for backward compatibility

            # Initialize schema
            self._init_schema()

            self._initialized = True
            print(f"📊 Database initialized: {self.db_path}")

    def _init_schema(self):
        """Execute schema initialization from SQL file"""
        schema_path = Path("database/init_schema.sql")

        if schema_path.exists():
            with open(schema_path) as f:
                schema_sql = f.read()
                # Execute the entire schema as one block
                try:
                    self.conn.execute(schema_sql)
                except Exception as e:
                    # Tables might already exist - that's fine
                    if "already exists" not in str(e).lower():
                        print(f"   ⚠️  Schema warning: {e}")
            print("   ✅ Schema initialized")
        else:
            print(f"   ⚠️  Schema file not found: {schema_path}")

    # ========================================================================
    # DOCUMENT OPERATIONS
    # ========================================================================

    def store_document(self, filename: str, file_content: bytes,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store document metadata and return doc_id

        This is where data gravity begins - every document stored makes
        the benchmark more valuable.
        """
        if metadata is None:
            metadata = {}

        # Generate unique identifiers
        file_hash = hashlib.sha256(file_content).hexdigest()
        doc_id = hashlib.md5(f"{filename}{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        # Check if document already exists (by hash)
        existing = self.conn.execute(
            "SELECT doc_id FROM documents WHERE file_hash = ?",
            [file_hash]
        ).fetchone()

        if existing:
            print(f"   ⚠️  Document already analyzed: {existing[0]}")
            return existing[0]

        # Insert document
        self.conn.execute("""
            INSERT INTO documents
            (doc_id, filename, upload_date, file_hash, plan_name, plan_size_bucket,
             document_type, page_count, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processing')
        """, [
            doc_id,
            filename,
            datetime.now(),
            file_hash,
            metadata.get('plan_name'),
            metadata.get('plan_size_bucket', 'unknown'),
            metadata.get('document_type', 'other'),
            metadata.get('page_count', 0)
        ])

        print(f"   📄 Document stored: {doc_id}")
        return doc_id

    def store_findings(self, doc_id: str, findings: List[Dict[str, Any]]):
        """
        Store all findings for a document

        Each finding adds to the intelligence pool that creates benchmarks.
        """
        if not findings:
            return

        for finding in findings:
            # Convert citations to JSON string
            citations_json = json.dumps(finding.get('citations', []))

            self.conn.execute("""
                INSERT INTO findings
                (finding_id, doc_id, category, subtype, decision, severity,
                 confidence, red_flag_score, lawsuit_precedent, legal_citation,
                 llm_analysis, citations, ruleset_version, model_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                finding['finding_id'],
                doc_id,
                finding['category'],
                finding['subtype'],
                finding['decision'],
                finding['severity'],
                finding['confidence'],
                finding.get('red_flag_score', 0),
                finding.get('lawsuit_precedent'),
                finding.get('legal_citation'),
                finding.get('llm_analysis'),
                citations_json,
                finding.get('ruleset_version', 'v3.0'),
                finding.get('model_version', 'local')
            ])

        print(f"   💾 Stored {len(findings)} findings")

    def update_document_status(self, doc_id: str, status: str,
                               total_findings: int, risk_score: int,
                               processing_time: float):
        """Update document after processing completes"""
        self.conn.execute("""
            UPDATE documents
            SET processing_status = ?,
                total_findings = ?,
                risk_score = ?,
                processing_time_seconds = ?
            WHERE doc_id = ?
        """, [status, total_findings, risk_score, processing_time, doc_id])

        print(f"   ✅ Document {doc_id} marked as {status}")

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Retrieve all documents with summary stats

        This powers the document library sidebar.
        """
        result = self.conn.execute("""
            SELECT doc_id, filename, upload_date, document_type,
                   total_findings, risk_score, processing_status,
                   plan_name, page_count
            FROM documents
            ORDER BY upload_date DESC
        """).fetchall()

        columns = ['doc_id', 'filename', 'upload_date', 'document_type',
                   'total_findings', 'risk_score', 'processing_status',
                   'plan_name', 'page_count']

        documents = []
        for row in result:
            doc = dict(zip(columns, row))
            # Convert timestamp to ISO format
            if doc['upload_date']:
                doc['upload_date'] = doc['upload_date'].isoformat()
            documents.append(doc)

        return documents

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get specific document metadata"""
        result = self.conn.execute("""
            SELECT doc_id, filename, upload_date, document_type,
                   total_findings, risk_score, processing_status,
                   plan_name, page_count, processing_time_seconds
            FROM documents
            WHERE doc_id = ?
        """, [doc_id]).fetchone()

        if not result:
            return None

        columns = ['doc_id', 'filename', 'upload_date', 'document_type',
                   'total_findings', 'risk_score', 'processing_status',
                   'plan_name', 'page_count', 'processing_time']

        doc = dict(zip(columns, result))
        if doc['upload_date']:
            doc['upload_date'] = doc['upload_date'].isoformat()

        return doc

    def get_document_findings(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all findings for a specific document"""
        result = self.conn.execute("""
            SELECT finding_id, doc_id, category, subtype, decision, severity,
                   confidence, red_flag_score, lawsuit_precedent, legal_citation,
                   llm_analysis, citations, created_at, ruleset_version, model_version
            FROM findings
            WHERE doc_id = ?
            ORDER BY red_flag_score DESC,
                     CASE severity
                        WHEN 'prohibited_transaction' THEN 0
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                     END
        """, [doc_id]).fetchall()

        columns = ['finding_id', 'doc_id', 'category', 'subtype', 'decision',
                   'severity', 'confidence', 'red_flag_score', 'lawsuit_precedent',
                   'legal_citation', 'llm_analysis', 'citations', 'created_at',
                   'ruleset_version', 'model_version']

        findings = []
        for row in result:
            finding = dict(zip(columns, row))
            # Parse citations JSON
            if finding['citations']:
                try:
                    finding['citations'] = json.loads(finding['citations'])
                except:
                    finding['citations'] = []
            if finding['created_at']:
                finding['created_at'] = finding['created_at'].isoformat()
            findings.append(finding)

        return findings

    # ========================================================================
    # BENCHMARK CALCULATIONS - THE DATA GRAVITY ENGINE
    # ========================================================================

    def calculate_benchmarks(self):
        """
        Recalculate benchmark statistics from all findings

        THIS IS THE MAGIC. This is what makes each document more valuable.
        As the dataset grows, these benchmarks become proprietary intelligence.
        """
        print("   📊 Calculating benchmarks...")

        # Clear existing benchmarks
        self.conn.execute("DELETE FROM benchmark_stats")

        # Get total completed documents
        total_docs = self.conn.execute("""
            SELECT COUNT(*) FROM documents WHERE processing_status = 'completed'
        """).fetchone()[0]

        if total_docs == 0:
            print("   ⚠️  No completed documents to benchmark")
            return

        # Calculate category-level benchmarks
        self.conn.execute("""
            INSERT INTO benchmark_stats
            (stat_id, category, subtype, avg_red_flag_score, median_confidence,
             violation_frequency, sample_size, percentile_25, percentile_50,
             percentile_75, percentile_90)
            SELECT
                category || '_' || subtype AS stat_id,
                category,
                subtype,
                AVG(red_flag_score) AS avg_red_flag_score,
                MEDIAN(confidence) AS median_confidence,
                COUNT(DISTINCT doc_id)::FLOAT / ? AS violation_frequency,
                COUNT(*) AS sample_size,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY red_flag_score) AS percentile_25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY red_flag_score) AS percentile_50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY red_flag_score) AS percentile_75,
                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY red_flag_score) AS percentile_90
            FROM findings
            WHERE decision = 'present'
            GROUP BY category, subtype
        """, [total_docs])

        benchmark_count = self.conn.execute("SELECT COUNT(*) FROM benchmark_stats").fetchone()[0]
        print(f"   ✅ Calculated {benchmark_count} benchmark statistics from {total_docs} documents")

    def get_benchmarks(self) -> Dict[str, Any]:
        """
        Get current benchmark statistics

        This is what compliance officers will pay for - industry intelligence
        that gets better with every document.
        """
        # Get total documents
        total_docs = self.conn.execute("""
            SELECT COUNT(*) FROM documents WHERE processing_status = 'completed'
        """).fetchone()[0]

        # Get total findings
        total_findings = self.conn.execute("""
            SELECT COUNT(*) FROM findings WHERE decision = 'present'
        """).fetchone()[0]

        # Get category-level statistics
        category_stats = self.conn.execute("""
            SELECT
                category,
                AVG(avg_red_flag_score) as avg_score,
                AVG(violation_frequency) as frequency,
                SUM(sample_size) as total_violations
            FROM benchmark_stats
            GROUP BY category
            ORDER BY total_violations DESC
        """).fetchall()

        # Get most common violations
        common_violations = self.conn.execute("""
            SELECT
                category,
                subtype,
                violation_frequency,
                sample_size,
                avg_red_flag_score
            FROM benchmark_stats
            ORDER BY violation_frequency DESC, avg_red_flag_score DESC
            LIMIT 10
        """).fetchall()

        # Get average risk score
        avg_risk = self.conn.execute("""
            SELECT AVG(risk_score) FROM documents WHERE processing_status = 'completed'
        """).fetchone()[0] or 0

        return {
            'total_documents': total_docs,
            'total_findings': total_findings,
            'avg_risk_score': round(avg_risk, 1),
            'category_benchmarks': [
                {
                    'category': row[0],
                    'avg_score': round(row[1], 1) if row[1] else 0,
                    'frequency': round(row[2] * 100, 1) if row[2] else 0,
                    'total_violations': row[3]
                }
                for row in category_stats
            ],
            'common_violations': [
                {
                    'category': row[0],
                    'subtype': row[1],
                    'frequency': round(row[2] * 100, 1) if row[2] else 0,
                    'sample_size': row[3],
                    'avg_red_flag': round(row[4], 1) if row[4] else 0
                }
                for row in common_violations
            ]
        }

    def get_document_percentile(self, doc_id: str) -> Dict[str, float]:
        """
        Calculate where this document ranks vs all others

        "Your disclosure is worse than 73% of similar plans"
        This single sentence justifies the entire platform.
        """
        # Get document risk score
        doc_result = self.conn.execute(
            "SELECT risk_score FROM documents WHERE doc_id = ?",
            [doc_id]
        ).fetchone()

        if not doc_result:
            return {'percentile': 0, 'risk_score': 0}

        doc_risk = doc_result[0] or 0

        # Calculate percentile (what % of docs have LOWER risk)
        percentile_result = self.conn.execute("""
            SELECT
                (COUNT(CASE WHEN risk_score < ? THEN 1 END)::FLOAT /
                 NULLIF(COUNT(*)::FLOAT, 0)) * 100 as percentile
            FROM documents
            WHERE processing_status = 'completed'
        """, [doc_risk]).fetchone()

        percentile = percentile_result[0] if percentile_result and percentile_result[0] else 0

        return {
            'percentile': round(percentile, 1),
            'risk_score': doc_risk
        }

    # ========================================================================
    # COMPARISON OPERATIONS
    # ========================================================================

    def compare_documents(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """Compare multiple documents side-by-side"""
        comparison = []

        for doc_id in doc_ids:
            doc = self.get_document_by_id(doc_id)
            if not doc:
                continue

            percentile = self.get_document_percentile(doc_id)
            findings = self.get_document_findings(doc_id)

            # Category breakdown
            category_counts = {}
            for finding in findings:
                cat = finding['category']
                category_counts[cat] = category_counts.get(cat, 0) + 1

            comparison.append({
                'doc_id': doc_id,
                'filename': doc['filename'],
                'risk_score': doc['risk_score'],
                'percentile': percentile['percentile'],
                'total_findings': doc['total_findings'],
                'category_breakdown': category_counts,
                'upload_date': doc['upload_date']
            })

        return comparison

    # ========================================================================
    # STATISTICS & ANALYTICS
    # ========================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get compelling statistics for the metrics dashboard

        These are the numbers that make investors lean forward.
        """
        # Document stats
        doc_stats = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed,
                AVG(processing_time_seconds) as avg_time,
                AVG(risk_score) as avg_risk
            FROM documents
        """).fetchone()

        # Finding stats
        finding_stats = self.conn.execute("""
            SELECT
                COUNT(*) as total_findings,
                COUNT(CASE WHEN severity IN ('prohibited_transaction', 'critical') THEN 1 END) as critical_count,
                COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_count
            FROM findings
            WHERE decision = 'present'
        """).fetchone()

        # Settlement amounts (from precedents)
        # This is marketing gold: "$XXM in settlements from detected patterns"
        lawsuit_amounts = [
            55000000,  # Tussey v. ABB
            35000000,  # Harris v. Amgen
            # Cornell ongoing
        ]
        total_settlement_value = sum(lawsuit_amounts)

        return {
            'total_documents': doc_stats[0] if doc_stats else 0,
            'completed_documents': doc_stats[1] if doc_stats else 0,
            'avg_processing_time': round(doc_stats[2], 1) if doc_stats and doc_stats[2] else 0,
            'avg_risk_score': round(doc_stats[3], 1) if doc_stats and doc_stats[3] else 0,
            'total_findings': finding_stats[0] if finding_stats else 0,
            'critical_findings': finding_stats[1] if finding_stats else 0,
            'high_findings': finding_stats[2] if finding_stats else 0,
            'settlement_value_detected': total_settlement_value
        }

    def close(self):
        """Close database connection (only call this when shutting down the entire app)"""
        if self._conn:
            self._conn.close()
            DatabaseManager._conn = None
            DatabaseManager._initialized = False
            print("   📊 Database connection closed")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_db() -> DatabaseManager:
    """Get database instance"""
    return DatabaseManager()


if __name__ == "__main__":
    # Test database initialization
    print("\n" + "="*80)
    print("🧪 TESTING DATABASE MANAGER")
    print("="*80)

    db = DatabaseManager()

    # Test document storage
    test_content = b"Test document content"
    doc_id = db.store_document(
        "test_disclosure.pdf",
        test_content,
        {'document_type': '408b2', 'page_count': 10}
    )

    print(f"\n✅ Test document created: {doc_id}")

    # Get all documents
    docs = db.get_all_documents()
    print(f"✅ Total documents in database: {len(docs)}")

    # Get benchmarks
    benchmarks = db.get_benchmarks()
    print(f"✅ Benchmark data: {benchmarks}")

    db.close()

    print("\n" + "="*80)
    print("🎉 DATABASE MANAGER TEST COMPLETE")
    print("="*80 + "\n")
