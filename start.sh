#!/bin/bash

echo "================================"
echo "🔥 COLA II v3 FINAL - Starting..."
echo "================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python 3 found"

# Check if requirements are installed
echo "📦 Checking dependencies..."

if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip install -r requirements.txt --break-system-packages
else
    echo "✅ Dependencies installed"
fi

# Check if files exist
if [ ! -f "backend_FINAL.py" ]; then
    echo "❌ backend_FINAL.py not found!"
    exit 1
fi

if [ ! -f "detection_engine_v3_FINAL.py" ]; then
    echo "❌ detection_engine_v3_FINAL.py not found!"
    exit 1
fi

if [ ! -f "generate_pdf_report_FINAL.py" ]; then
    echo "❌ generate_pdf_report_FINAL.py not found!"
    exit 1
fi

if [ ! -f "index.html" ]; then
    echo "⚠️  index.html not found - API will still work"
fi

echo "✅ Core files found"
echo ""

# Create directories
mkdir -p uploads outputs audits
echo "✅ Directories created"
echo ""

# Start server
echo "================================"
echo "🚀 Starting COLA II v3 Backend"
echo "================================"
echo ""
echo "🌐 Server: http://localhost:5001"
echo "📡 API: http://localhost:5001/api/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 backend_FINAL.py
