import sqlite3
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = r"C:\Users\scott\OneDrive\Documents\SWGSales\swg.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factory_lines (
            id TEXT PRIMARY KEY,
            name TEXT,
            color_idx INTEGER,
            product TEXT,
            tpu REAL,
            unit TEXT,
            qty INTEGER,
            status TEXT DEFAULT 'idle',
            started_at INTEGER,
            total_sec REAL,
            sort_order INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factory_history (
            id TEXT PRIMARY KEY,
            product TEXT,
            tpu REAL,
            unit TEXT,
            qty INTEGER,
            created_at INTEGER
        )
    """)
    conn.commit()
    conn.close()


# ── Lines ─────────────────────────────────────────────────────────────────────

@app.route('/api/lines', methods=['GET'])
def get_lines():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM factory_lines ORDER BY sort_order ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/lines', methods=['POST'])
def save_lines():
    lines = request.json
    conn = get_conn()
    conn.execute("DELETE FROM factory_lines")
    for i, line in enumerate(lines):
        conn.execute("""
            INSERT OR REPLACE INTO factory_lines
            (id, name, color_idx, product, tpu, unit, qty, status, started_at, total_sec, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            line.get('id'),
            line.get('name'),
            line.get('colorIdx', 0),
            line.get('product', ''),
            line.get('tpu'),
            line.get('unit', 'sec'),
            line.get('qty'),
            line.get('status', 'idle'),
            line.get('startedAt'),
            line.get('totalSec', 0),
            i
        ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── History ───────────────────────────────────────────────────────────────────

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM factory_history ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/history', methods=['POST'])
def save_history():
    history = request.json
    conn = get_conn()
    conn.execute("DELETE FROM factory_history")
    for h in history:
        conn.execute("""
            INSERT OR REPLACE INTO factory_history (id, product, tpu, unit, qty, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            h.get('id'),
            h.get('product', ''),
            h.get('tpu'),
            h.get('unit', 'sec'),
            h.get('qty'),
            h.get('createdAt', 0)
        ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    create_tables()
    print("Factory API running at http://localhost:5050")
    app.run(port=5050, debug=False)