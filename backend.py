#!/usr/bin/env python3
"""
COLA II v3 FINAL - Main Backend with Multi-Document Persistence
Integrated Flask API with v3 detection + PDF reports + Data Gravity
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json
import time
import signal
import atexit

# Flask
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# Database for multi-document persistence
from database.db_manager import DatabaseManager

# PDF Processing
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  WARNING: PyMuPDF not installed. Install with: pip install PyMuPDF")

# Detection Engine v3
from detection_engine_v3 import (
    DetectionEngineV3,
    DocumentPage,
    Finding,
    findings_summary
)

# PDF Report Generation
try:
    from generate_pdf_report import generate_compliance_report
    PDF_REPORT_SUPPORT = True
except ImportError:
    PDF_REPORT_SUPPORT = False
    print("⚠️  WARNING: PDF report generator not found")

# ============================================================================
# CONFIGURATION
# ============================================================================

APP_VERSION = "3.0.0-FINAL"
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
AUDIT_DIR = Path("audits")

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
AUDIT_DIR.mkdir(exist_ok=True)

MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# Flask app
app = Flask(__name__, static_folder='.')
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# CORS - allow all for demo
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize v3 detection engine 🔥
print("\n" + "="*80)
print("🔥 COLA II v3 FINAL - Initializing Lawsuit-Trained Detection Engine")
print("="*80)

detection_engine = DetectionEngineV3()
print(f"✅ v3 Engine Ready")
print(f"   Ruleset: {detection_engine.ruleset_version}")
print(f"   Model: {detection_engine.model_version}")
print(f"   PDF Support: {PDF_SUPPORT}")
print(f"   PDF Reports: {PDF_REPORT_SUPPORT}")

# ============================================================================
# DATABASE INITIALIZATION - SINGLETON PATTERN
# ============================================================================

print("\n💾 Initializing Multi-Document Database...")
print("   Using singleton pattern - one connection for all operations")

try:
    # Initialize database ONCE at startup (singleton pattern ensures single connection)
    db = DatabaseManager()
    print("✅ Database Ready - Data Gravity Enabled")
    print(f"   Database path: {db.db_path}")
except Exception as e:
    print(f"❌ FATAL: Could not initialize database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*80 + "\n")


# ============================================================================
# SHUTDOWN HANDLERS - PREVENT LOCK FILES
# ============================================================================

def cleanup_database():
    """Clean shutdown of database connection"""
    try:
        print("\n🔄 Shutting down database connection...")
        db.close()
        print("✅ Database closed cleanly")
    except Exception as e:
        print(f"⚠️  Warning during shutdown: {e}")

def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print(f"\n⚠️  Received signal {signum}, shutting down gracefully...")
    cleanup_database()
    sys.exit(0)

# Register shutdown handlers
atexit.register(cleanup_database)
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Kill command

print("✅ Shutdown handlers registered - database will close cleanly")
print("="*80 + "\n")


# ============================================================================
# PDF PARSING
# ============================================================================

def extract_pages_with_layout(pdf_path: Path) -> List[DocumentPage]:
    """Extract text and layout information from PDF"""
    pages = []
    
    if not PDF_SUPPORT:
        return [DocumentPage(
            page_no=1,
            text="PDF support not available - install PyMuPDF",
            blocks=[],
            tables=[]
        )]
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract blocks
            blocks = []
            text_dict = page.get_text("dict")
            
            full_text = ""
            for block_idx, block in enumerate(text_dict.get("blocks", [])):
                if "lines" in block:
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"] + " "
                    
                    blocks.append({
                        "block_id": f"b{page_num}_{block_idx}",
                        "text": block_text.strip(),
                        "bbox": block.get("bbox", [0, 0, 0, 0])
                    })
                    full_text += block_text + "\n"
            
            pages.append(DocumentPage(
                page_no=page_num + 1,
                text=full_text.strip(),
                blocks=blocks,
                tables=[]
            ))
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Error parsing PDF: {e}")
        pages.append(DocumentPage(
            page_no=1,
            text=f"Error parsing PDF: {str(e)}",
            blocks=[],
            tables=[]
        ))
    
    return pages


# ============================================================================
# SMART DEDUPLICATION - GROUP IDENTICAL FINDINGS
# ============================================================================

def deduplicate_findings(findings: List[Dict]) -> Dict:
    """
    Group identical findings to avoid showing "Revenue sharing (6 instances)"
    as 6 separate cards.

    Groups by: llm_analysis + category + severity
    Returns: grouped_findings structure with instances counted
    """
    from collections import defaultdict
    import hashlib

    # Group findings by their "signature"
    groups = defaultdict(list)

    for finding in findings:
        # Create signature from analysis text + category + severity
        signature = f"{finding.get('llm_analysis', '')}_{finding.get('category', '')}_{finding.get('severity', '')}"
        group_id = hashlib.md5(signature.encode()).hexdigest()[:12]

        groups[group_id].append(finding)

    # Build grouped structure
    grouped_findings = []

    for group_id, group_findings in groups.items():
        instance_count = len(group_findings)
        first_finding = group_findings[0]

        # Collect all pages and excerpts
        pages = []
        excerpts = []

        for f in group_findings:
            citations = f.get('citations', [])
            for citation in citations:
                page_no = citation.get('page_no', 0)
                if page_no and page_no not in pages:
                    pages.append(page_no)
                excerpt = citation.get('excerpt', '')
                if excerpt and excerpt not in excerpts:
                    excerpts.append(excerpt[:100])

        pages.sort()

        # Create consolidated finding
        grouped_finding = {
            **first_finding,
            'dedup_group_id': group_id,
            'instance_count': instance_count,
            'consolidated_pages': pages,
            'consolidated_excerpts': excerpts[:3],  # Limit to 3 examples
            'all_instances': group_findings  # Keep originals for PDF
        }

        grouped_findings.append(grouped_finding)

    # Sort by severity and instance count
    severity_order = {
        'prohibited_transaction': 0,
        'critical': 1,
        'high': 2,
        'medium': 3,
        'low': 4
    }

    grouped_findings.sort(
        key=lambda x: (
            severity_order.get(x.get('severity', 'low'), 5),
            -x.get('instance_count', 1)
        )
    )

    return {
        'grouped_findings': grouped_findings,
        'total_unique_issues': len(grouped_findings),
        'total_instances': len(findings)
    }


# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================

def process_document(pdf_path: Path, doc_id: Optional[str] = None) -> Dict:
    """Process PDF with v3 engine and generate report"""
    
    if doc_id is None:
        doc_id = f"doc_{pdf_path.stem}"
    
    print(f"\n📄 Processing: {pdf_path.name}")
    
    # 1. Extract pages
    print("   📖 Extracting pages...")
    pages = extract_pages_with_layout(pdf_path)
    print(f"   ✅ Extracted {len(pages)} pages")
    
    if not pages or pages[0].text.startswith("Error"):
        return {
            "error": "Failed to extract pages from PDF",
            "summary": {"total_findings": 0},
            "findings": []
        }
    
    # 2. Run v3 detection
    timestamp = datetime.utcnow().isoformat() + "Z"
    print("   🔬 Running v3 lawsuit-trained analysis...")
    findings = detection_engine.analyze_document(doc_id, pages, timestamp)
    print(f"   ✅ Found {len(findings)} issues")
    
    # 3. Generate summary
    summary = findings_summary(findings)
    print(f"   📊 Risk Score: {summary.get('lawsuit_risk_score', 0)}/100")

    # 4. Convert findings to dicts
    findings_dicts = [f.to_dict() for f in findings]

    # 5. Apply smart deduplication
    dedup_result = deduplicate_findings(findings_dicts)
    print(f"   🔄 Deduplicated: {dedup_result['total_instances']} → {dedup_result['total_unique_issues']} unique issues")

    # 6. Create result
    result = {
        "document": pdf_path.name,
        "doc_id": doc_id,
        "timestamp": timestamp,
        "pages": len(pages),
        "analyzer_version": APP_VERSION,
        "engine": "v3-lawsuit-trained",
        "summary": summary,
        "findings": findings_dicts,  # Original findings for database
        "grouped_findings": dedup_result['grouped_findings'],  # Grouped for UI
        "total_unique_issues": dedup_result['total_unique_issues'],
        "total_instances": dedup_result['total_instances']
    }

    return result


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Serve the main HTML interface"""
    try:
        return send_file('index.html')
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>COLA II v3</title></head>
        <body style="font-family: Arial; padding: 50px; background: #1a1a1a; color: #fff;">
            <h1>🔥 COLA II v3 API</h1>
            <p>Backend is running. Upload index.html to this directory for the full UI.</p>
            <h2>API Endpoints:</h2>
            <ul>
                <li>POST /api/upload - Upload PDF for analysis</li>
                <li>GET /api/health - Health check</li>
                <li>POST /api/demo - Analyze demo document</li>
                <li>GET /api/audit_log - View audit log</li>
            </ul>
        </body>
        </html>
        """, 200


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint with database status"""
    try:
        # Test database connection by getting document count
        docs = db.get_all_documents()
        db_status = "connected"
        db_error = None
        document_count = len(docs)
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        document_count = 0

    # Determine overall status
    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    response = {
        "status": overall_status,
        "version": APP_VERSION,
        "engine": "v3-lawsuit-trained",
        "ruleset_version": detection_engine.ruleset_version,
        "database": {
            "status": db_status,
            "documents": document_count,
            "path": db.db_path
        },
        "pdf_support": PDF_SUPPORT,
        "pdf_report_support": PDF_REPORT_SUPPORT,
        "features": {
            "lawsuit_patterns": "70+ patterns from Tussey, Cornell, Harris",
            "risk_scoring": "Lawsuit risk + obfuscation scores",
            "pdf_reports": "Professional 10-page compliance reports"
        }
    }

    if db_error:
        response["database"]["error"] = db_error

    status_code = 200 if overall_status == "healthy" else 500
    return jsonify(response), status_code


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and analyze PDF with v3 engine + multi-document persistence"""

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files supported"}), 400

    try:
        filename = file.filename

        # Read file content for hashing (detect duplicates)
        file_content = file.read()
        file.seek(0)  # Reset for saving

        # Get optional metadata from form (including new client tagging fields)
        metadata = {
            'document_type': request.form.get('doc_type', 'other'),
            'plan_name': request.form.get('plan_name'),
            'plan_size_bucket': request.form.get('plan_size', 'unknown'),
            'client_tag': request.form.get('client_tag'),  # NEW: Client/project name
            'is_benchmark_eligible': request.form.get('is_benchmark', 'true').lower() == 'true',  # NEW: Include in benchmarks
            'plan_size_category': request.form.get('plan_size_category'),  # NEW: For peer grouping
            'plan_industry': request.form.get('plan_industry')  # NEW: Industry classification
        }

        print(f"\n{'='*80}")
        print(f"🚀 NEW UPLOAD: {filename}")
        print(f"{'='*80}")

        # Store document in database (get doc_id)
        try:
            doc_id = db.store_document(filename, file_content, metadata)
        except Exception as e:
            print(f"❌ Database error storing document: {e}")
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        # Save file physically
        upload_path = UPLOAD_DIR / f"{doc_id}_{filename}"
        file.save(str(upload_path))

        # Process with v3 detection engine
        start_time = time.time()

        result = process_document(upload_path, doc_id=doc_id)

        processing_time = time.time() - start_time

        # Update page count in metadata if available
        if 'pages' in result:
            metadata['page_count'] = result['pages']

        # Store findings in database
        try:
            db.store_findings(doc_id, result['findings'])
        except Exception as e:
            print(f"❌ Database error storing findings: {e}")
            return jsonify({'error': f'Database error storing findings: {str(e)}'}), 500

        # Calculate risk score
        risk_score = result['summary'].get('lawsuit_risk_score', 0)

        # Update document status
        try:
            db.update_document_status(
                doc_id=doc_id,
                status='completed',
                total_findings=result['summary']['total_findings'],
                risk_score=risk_score,
                processing_time=processing_time
            )
        except Exception as e:
            print(f"❌ Database error updating status: {e}")
            return jsonify({'error': f'Database error updating status: {str(e)}'}), 500

        # Recalculate benchmarks (DATA GRAVITY!)
        try:
            db.calculate_benchmarks()
        except Exception as e:
            print(f"⚠️  Warning: Could not recalculate benchmarks: {e}")
            # Non-fatal, continue

        # Get percentile ranking
        try:
            percentile_data = db.get_document_percentile(doc_id)
            result['percentile'] = percentile_data
        except Exception as e:
            print(f"⚠️  Warning: Could not calculate percentile: {e}")
            result['percentile'] = {'percentile': 0, 'risk_score': risk_score}

        # Save JSON results
        output_json = OUTPUT_DIR / f"{doc_id}_findings.json"
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=2)

        result['findings_json'] = str(output_json)

        # Generate PDF report if available
        if PDF_REPORT_SUPPORT and len(result['findings']) > 0:
            try:
                pdf_report = OUTPUT_DIR / f"{doc_id}_COMPLIANCE_REPORT.pdf"
                print(f"   📑 Generating PDF compliance report...")

                generate_compliance_report(
                    findings_data=result,
                    output_path=str(pdf_report)
                )

                result['pdf_report'] = str(pdf_report)
                print(f"   ✅ PDF report: {pdf_report.name}")
            except Exception as e:
                print(f"   ⚠️  PDF report generation failed: {e}")

        # Audit log
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "analyze_v3",
            "doc_id": doc_id,
            "document": filename,
            "findings_count": result["summary"]["total_findings"],
            "high_severity_count": result["summary"].get("high_severity_count", 0),
            "lawsuit_risk_score": risk_score,
            "percentile": percentile_data['percentile']
        }

        with open(AUDIT_DIR / "log.jsonl", 'a') as f:
            f.write(json.dumps(audit_entry) + "\n")

        print(f"{'='*80}\n")

        return jsonify(result)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/demo', methods=['POST'])
def demo_analyze():
    """Analyze demo_test.pdf with v3"""
    demo_path = Path("demo_test.pdf")
    
    if not demo_path.exists():
        return jsonify({"error": "demo_test.pdf not found in current directory"}), 404
    
    try:
        print(f"\n{'='*80}")
        print(f"🎬 DEMO ANALYSIS")
        print(f"{'='*80}")
        
        result = process_document(demo_path, doc_id="doc_demo_test")
        
        # Save results
        output_json = OUTPUT_DIR / "demo_test_findings.json"
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Generate PDF report
        if PDF_REPORT_SUPPORT:
            try:
                pdf_report = OUTPUT_DIR / "demo_test_COMPLIANCE_REPORT.pdf"
                generate_compliance_report(result, str(pdf_report))
                result['pdf_report'] = str(pdf_report)
            except Exception as e:
                print(f"   ⚠️  PDF report generation failed: {e}")
        
        print(f"{'='*80}\n")
        
        return jsonify(result)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/audit_log', methods=['GET'])
def get_audit_log():
    """Retrieve audit log"""
    log_path = AUDIT_DIR / "log.jsonl"
    
    if not log_path.exists():
        return jsonify({"entries": []})
    
    entries = []
    with open(log_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    limit = request.args.get('limit', type=int, default=50)
    return jsonify({"entries": entries[-limit:]})


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download generated reports"""
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """
    List all analyzed documents

    This powers the document library sidebar - the visual proof of data gravity
    """
    try:
        documents = db.get_all_documents()
        return jsonify({
            'documents': documents,
            'total': len(documents)
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/document/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    Get specific document with findings and percentile ranking

    This is where users see: "Worse than 73% of similar plans"
    """
    try:
        # Get document metadata
        document = db.get_document_by_id(doc_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404

        # Get findings
        findings = db.get_document_findings(doc_id)

        # Get percentile ranking
        percentile = db.get_document_percentile(doc_id)

        return jsonify({
            'document': document,
            'findings': findings,
            'percentile': percentile,
            'total_findings': len(findings)
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/benchmarks', methods=['GET'])
def get_benchmarks():
    """
    Get aggregate benchmark statistics

    This is the DATA GRAVITY - proprietary intelligence that compounds with every upload
    """
    try:
        benchmarks = db.get_benchmarks()
        return jsonify(benchmarks)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/compare', methods=['POST'])
def compare_documents():
    """
    Compare multiple documents side-by-side

    Perfect for RIAs comparing multiple plan disclosures
    """
    try:
        data = request.get_json()
        if not data or 'doc_ids' not in data:
            return jsonify({"error": "No doc_ids provided"}), 400

        doc_ids = data['doc_ids']
        if not isinstance(doc_ids, list):
            return jsonify({"error": "doc_ids must be an array"}), 400

        comparison = db.compare_documents(doc_ids)

        return jsonify({
            'comparison': comparison,
            'total_compared': len(comparison)
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """
    Get dashboard statistics for the metrics panel

    These are the numbers that make investors lean forward
    """
    try:
        stats = db.get_dashboard_stats()
        benchmarks = db.get_benchmarks()

        return jsonify({
            'stats': stats,
            'benchmarks': benchmarks
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/generate-report/<doc_id>', methods=['POST'])
def generate_report(doc_id):
    """
    Generate PDF compliance report on-demand for a specific document

    This endpoint allows users to regenerate or download compliance reports
    for previously analyzed documents without re-analyzing the entire document.
    """
    try:
        # Check if PDF report generation is available
        if not PDF_REPORT_SUPPORT:
            return jsonify({
                "error": "PDF report generation not available",
                "message": "Install required packages: pip install reportlab"
            }), 503

        # Get document metadata
        document = db.get_document_by_id(doc_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404

        # Get findings
        findings = db.get_document_findings(doc_id)

        # Get percentile ranking
        try:
            percentile = db.get_document_percentile(doc_id)
        except Exception as e:
            print(f"⚠️  Warning: Could not calculate percentile: {e}")
            percentile = {'percentile': 0, 'risk_score': document['risk_score']}

        # Build findings summary from database data
        by_category = {}
        by_severity = {}
        high_severity_count = 0
        total_confidence = 0

        for finding in findings:
            # Count by category
            cat = finding.get('category', 'unknown')
            by_category[cat] = by_category.get(cat, 0) + 1

            # Count by severity
            sev = finding.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1

            # Count high severity
            if sev in ['prohibited_transaction', 'critical', 'high']:
                high_severity_count += 1

            # Sum confidence
            total_confidence += finding.get('confidence', 0)

        avg_confidence = total_confidence / len(findings) if findings else 0

        # Create findings data structure matching the expected format
        findings_data = {
            "document": document['filename'],
            "doc_id": doc_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pages": document.get('page_count', 0),
            "analyzer_version": APP_VERSION,
            "engine": "v3-lawsuit-trained",
            "summary": {
                "total_findings": len(findings),
                "by_category": by_category,
                "by_severity": by_severity,
                "avg_confidence": avg_confidence,
                "high_severity_count": high_severity_count,
                "lawsuit_risk_score": document['risk_score']
            },
            "findings": findings,
            "percentile": percentile
        }

        # Generate PDF report
        pdf_filename = f"{doc_id}_COMPLIANCE_REPORT.pdf"
        pdf_path = OUTPUT_DIR / pdf_filename

        print(f"\n📑 Generating PDF report for {document['filename']}...")

        generate_compliance_report(
            findings_data=findings_data,
            output_path=str(pdf_path)
        )

        print(f"✅ PDF report generated: {pdf_filename}")

        # Return the PDF file for download
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{document['filename'].replace('.pdf', '')}_COMPLIANCE_REPORT.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"❌ ERROR generating report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/outputs/<path:filename>')
def serve_output(filename):
    """Serve files from outputs directory"""
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@app.route('/api/mark-reviewed/<finding_id>', methods=['POST'])
def mark_finding_reviewed(finding_id):
    """
    Mark a finding as reviewed by the user

    Production polish: Allow users to mark findings as "reviewed"
    so they can track progress
    """
    try:
        data = request.get_json() or {}
        reviewed_by = data.get('reviewed_by', 'user')

        # Update finding in database
        db.conn.execute("""
            UPDATE findings
            SET reviewed_by_user = TRUE,
                reviewed_at = ?,
                reviewed_by = ?
            WHERE finding_id = ?
        """, [datetime.utcnow(), reviewed_by, finding_id])

        return jsonify({
            'success': True,
            'finding_id': finding_id,
            'reviewed_at': datetime.utcnow().isoformat() + 'Z'
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/filter-documents', methods=['GET'])
def filter_documents():
    """
    Filter documents by client tag or benchmark status

    Production polish: Allow filtering by client/project
    """
    try:
        client_tag = request.args.get('client_tag')
        benchmark_only = request.args.get('benchmark_only', 'false').lower() == 'true'

        query = """
            SELECT doc_id, filename, upload_date, document_type,
                   total_findings, risk_score, processing_status,
                   plan_name, page_count, client_tag, is_benchmark_eligible
            FROM documents
            WHERE processing_status = 'completed'
        """

        params = []

        if client_tag:
            query += " AND client_tag = ?"
            params.append(client_tag)

        if benchmark_only:
            query += " AND is_benchmark_eligible = TRUE"

        query += " ORDER BY upload_date DESC"

        result = db.conn.execute(query, params).fetchall()

        columns = ['doc_id', 'filename', 'upload_date', 'document_type',
                   'total_findings', 'risk_score', 'processing_status',
                   'plan_name', 'page_count', 'client_tag', 'is_benchmark_eligible']

        documents = []
        for row in result:
            doc = dict(zip(columns, row))
            if doc['upload_date']:
                doc['upload_date'] = doc['upload_date'].isoformat()
            documents.append(doc)

        return jsonify({
            'documents': documents,
            'total': len(documents),
            'filter': {
                'client_tag': client_tag,
                'benchmark_only': benchmark_only
            }
        })
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🔥 COLA II v3 FINAL - STARTING SERVER")
    print("="*80)
    print(f"   Version: {APP_VERSION}")
    print(f"   Engine: {detection_engine.ruleset_version}")
    print(f"   Patterns: 70+ lawsuit-trained patterns")
    print(f"   PDF Support: {PDF_SUPPORT}")
    print(f"   PDF Reports: {PDF_REPORT_SUPPORT}")
    print("="*80)
    print()
    print("🌐 Server: http://localhost:5001")
    print("📡 API: http://localhost:5001/api/health")
    print()
    print("Ready for billion-dollar demo! 🚀")
    print("="*80 + "\n")
    
    app.run(debug=True, port=5001, host='0.0.0.0')
