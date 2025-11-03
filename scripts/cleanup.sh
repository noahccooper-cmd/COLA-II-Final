#!/bin/bash
echo "🧹 Cleaning up processes and locks..."

# Kill any Python processes
pkill -9 python3 2>/dev/null
pkill -9 Python 2>/dev/null

# Remove database locks
rm -f data/cola.duckdb.wal 2>/dev/null
rm -f data/cola.duckdb.tmp 2>/dev/null
rm -f data/.cola.duckdb.lock 2>/dev/null

# Remove the database entirely to start fresh
rm -f data/cola.duckdb 2>/dev/null

echo "✅ Cleanup complete"
