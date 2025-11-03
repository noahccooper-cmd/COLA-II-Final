# COLA II - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Server

```bash
python start_server.py
```

Server will start at: **http://localhost:5001**

### 3. Open Browser

Navigate to: `http://localhost:5001`

### 4. Upload Documents

1. Click **"Upload Document"** button
2. Select or drag-drop a PDF (408(b)(2) disclosure)
3. Wait for analysis (~8-15 seconds)
4. View findings, percentile ranking, and risk score

### 5. See Data Gravity in Action

- Upload 2-5 more documents
- Watch the **Dashboard** update with benchmarks
- Click into any document to see percentile rankings
- See violation frequencies across all documents

---

## For Graves Competition Demo

### Pre-Demo Checklist

1. **Prepare 5 test PDFs** (labeled 1-5 for easy reference)
2. **Clear database** (optional - for fresh demo):
   ```bash
   rm -f data/cola.duckdb
   ```
3. **Start server**:
   ```bash
   python start_server.py
   ```
4. **Open browser**: http://localhost:5001
5. **Verify** dashboard loads with 0 documents

### Demo Flow (2:45 minutes)

See `demo/GRAVES_DEMO_SCRIPT.md` for complete script.

**Quick sequence:**
1. Upload Document 1 → Show findings
2. Upload Documents 2-5 rapidly → Show benchmarks evolving
3. Click into Document 3 → Show percentile ranking
4. Explain: "This is data gravity - proprietary intelligence that compounds"

---

## Troubleshooting

### Server won't start

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```bash
pip install -r requirements.txt
```

### Database lock error

**Error:** `Could not set lock on file`

**Fix:**
```bash
pkill -9 python
rm -f data/cola.duckdb.wal
python start_server.py
```

### Port 5001 already in use

**Fix:**
```bash
# Find process using port 5001
lsof -ti:5001 | xargs kill -9

# Or change port in start_server.py
# app.run(host='0.0.0.0', port=5002, debug=False)
```

### PDF not processing

**Check:**
- File is actually a PDF (not just renamed)
- File size < 50MB
- File is not password-protected
- PyMuPDF installed: `pip install PyMuPDF`

---

## API Testing

### Health Check

```bash
curl http://localhost:5001/api/health
```

### List Documents

```bash
curl http://localhost:5001/api/documents
```

### Get Benchmarks

```bash
curl http://localhost:5001/api/benchmarks
```

### Get Dashboard Stats

```bash
curl http://localhost:5001/api/dashboard
```

---

## File Structure

```
cola-ii-final/
├── backend.py              # Main Flask API
├── start_server.py         # Production server launcher
├── detection_engine_v3.py  # 70+ lawsuit patterns
├── index.html              # Multi-document UI
├── database/
│   ├── init_schema.sql     # Database schema
│   └── db_manager.py       # Database operations
├── data/
│   └── cola.duckdb         # Document + findings storage
├── audits/
│   └── lawsuit-cases/
│       └── case_research.json  # Litigation research
├── demo/
│   └── GRAVES_DEMO_SCRIPT.md   # Competition demo script
└── docs/
    └── OBTAINING_REAL_DISCLOSURES.md  # How to get test docs
```

---

## Next Steps

1. **Get Test Documents**: See `docs/OBTAINING_REAL_DISCLOSURES.md`
2. **Practice Demo**: Use `demo/GRAVES_DEMO_SCRIPT.md`
3. **Review Patterns**: See `audits/lawsuit-cases/case_research.json`
4. **Customize**: Extend detection patterns in `detection_engine_v3.py`

---

## Need Help?

- **Documentation**: See `README.md` for complete details
- **Demo Script**: `demo/GRAVES_DEMO_SCRIPT.md`
- **Test Docs**: `docs/OBTAINING_REAL_DISCLOSURES.md`
- **API Reference**: Check `README.md` → API Endpoints section

---

**Ready to demo at Graves Competition? Let's build a billion-dollar moat! 🚀**
