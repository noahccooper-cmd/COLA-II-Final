#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Start COLA II server without Flask debug mode (avoids DuckDB lock issues)
"""

import sys
import os
import subprocess
from pathlib import Path

sys.path.insert(0, '.')

def run_cleanup():
    """Run cleanup script before starting server"""
    cleanup_script = Path("scripts/cleanup.sh")

    if cleanup_script.exists():
        print("\n🧹 Running pre-startup cleanup...")
        try:
            result = subprocess.run(
                ["bash", str(cleanup_script)],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except subprocess.TimeoutExpired:
            print("⚠️  Cleanup timed out, continuing anyway...")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")
    else:
        print(f"⚠️  Cleanup script not found: {cleanup_script}")

    print()


if __name__ == '__main__':
    # Run cleanup first to remove any stale locks
    run_cleanup()

    # Import the Flask app AFTER cleanup
    from backend import app

    print("🚀 Starting COLA II Server...")
    print("   Open browser to: http://localhost:5001")
    print("   Press Ctrl+C to stop\n")

    # Run without debug mode to avoid reloader causing DuckDB lock issues
    app.run(host='0.0.0.0', port=5001, debug=False)
