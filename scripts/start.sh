#!/bin/bash
echo "🚀 Starting COLA II..."

# Clean up first
./scripts/cleanup.sh

# Create necessary directories
mkdir -p data uploads audits outputs

# Start backend
echo "Starting backend server..."
python3 backend.py
