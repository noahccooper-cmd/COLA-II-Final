#!/usr/bin/env python3
"""
COLA II v3 FINAL - Main Backend
Integrated Flask API with v3 detection + PDF reports
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json

# Flask
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

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
    
    # 4. Create result
    result = {
        "document": pdf_path.name,
        "doc_id": doc_id,
        "timestamp": timestamp,
        "pages": len(pages),
        "analyzer_version": APP_VERSION,
        "engine": "v3-lawsuit-trained",
        "summary": summary,
        "findings": [f.to_dict() for f in findings]
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
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION,
        "engine": "v3-lawsuit-trained",
        "ruleset_version": detection_engine.ruleset_version,
        "pdf_support": PDF_SUPPORT,
        "pdf_report_support": PDF_REPORT_SUPPORT,
        "features": {
            "lawsuit_patterns": "70+ patterns from Tussey, Cornell, Harris",
            "risk_scoring": "Lawsuit risk + obfuscation scores",
            "pdf_reports": "Professional 10-page compliance reports"
        }
    })


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and analyze PDF with v3 engine"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files supported"}), 400
    
    try:
        filename = file.filename
        upload_path = UPLOAD_DIR / filename
        file.save(str(upload_path))
        
        # Process with v3
        print(f"\n{'='*80}")
        print(f"🚀 NEW UPLOAD: {filename}")
        print(f"{'='*80}")
        
        result = process_document(upload_path, doc_id=f"doc_{Path(filename).stem}")
        
        # Save JSON results
        output_json = OUTPUT_DIR / f"{Path(filename).stem}_findings.json"
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=2)
        
        result['findings_json'] = str(output_json)
        
        # Generate PDF report if available
        if PDF_REPORT_SUPPORT and len(result['findings']) > 0:
            try:
                pdf_report = OUTPUT_DIR / f"{Path(filename).stem}_COMPLIANCE_REPORT.pdf"
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
            "document": filename,
            "findings_count": result["summary"]["total_findings"],
            "high_severity_count": result["summary"].get("high_severity_count", 0),
            "lawsuit_risk_score": result["summary"].get("lawsuit_risk_score", 0)
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


@app.route('/outputs/<path:filename>')
def serve_output(filename):
    """Serve files from outputs directory"""
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


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
