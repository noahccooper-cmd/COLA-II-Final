#!/usr/bin/env python3
"""
Start COLA II server without Flask debug mode (avoids DuckDB lock issues)
"""

import sys
sys.path.insert(0, '.')

# Import the Flask app
from backend import app

if __name__ == '__main__':
    print("\n🚀 Starting COLA II Server...")
    print("   Open browser to: http://localhost:5001")
    print("   Press Ctrl+C to stop\n")

    # Run without debug mode to avoid reloader causing DuckDB lock issues
    app.run(host='0.0.0.0', port=5001, debug=False)
