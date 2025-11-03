#!/bin/bash
echo "🧹 Cleaning up processes and locks..."

# Find and kill only backend.py processes (preserve other Python processes)
echo "   🔍 Looking for backend.py processes..."
pgrep -f "backend.py" | while read pid; do
    echo "   💀 Killing backend.py process: $pid"
    kill -9 $pid 2>/dev/null
done

# Also check for start_server.py
pgrep -f "start_server.py" | while read pid; do
    echo "   💀 Killing start_server.py process: $pid"
    kill -9 $pid 2>/dev/null
done

# Give processes time to die
sleep 1

# Remove DuckDB lock files (but preserve the database!)
echo "   🔓 Removing lock files..."
rm -f data/cola.duckdb.wal 2>/dev/null
rm -f data/cola.duckdb.tmp 2>/dev/null
rm -f data/.cola.duckdb.lock 2>/dev/null
rm -f data/cola.duckdb-wal 2>/dev/null
rm -f data/cola.duckdb-shm 2>/dev/null

# DO NOT remove data/cola.duckdb - that's your actual data!
# Only remove locks, not the database itself

echo "✅ Cleanup complete - database preserved, locks removed"
echo "   Database: data/cola.duckdb $(test -f data/cola.duckdb && echo '✅ exists' || echo '⚠️  not found')"
