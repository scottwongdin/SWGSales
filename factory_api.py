import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
sys.path.insert(0, r"C:\Users\scott\OneDrive\Documents\SWGSales")
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

app = Flask(__name__)
CORS(app)


def get_conn():
    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, port=DB_PORT
    )
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def create_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS factory_lines (
            id TEXT PRIMARY KEY,
            name TEXT,
            color_idx INTEGER,
            product TEXT,
            tpu REAL,
            unit TEXT,
            qty INTEGER,
            status TEXT DEFAULT 'idle',
            started_at BIGINT,
            total_sec REAL,
            sort_order INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS factory_history (
            id TEXT PRIMARY KEY,
            product TEXT,
            tpu REAL,
            unit TEXT,
            qty INTEGER,
            created_at BIGINT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


# Lines

@app.route('/api/lines', methods=['GET'])
def get_lines():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM factory_lines ORDER BY sort_order ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/lines', methods=['POST'])
def save_lines():
    lines = request.json
    conn = get_conn()
    cur = conn.cursor()
    for i, line in enumerate(lines):
        cur.execute("""
            INSERT INTO factory_lines
            (id, name, color_idx, product, tpu, unit, qty, status, started_at, total_sec, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                color_idx = EXCLUDED.color_idx,
                product = EXCLUDED.product,
                tpu = EXCLUDED.tpu,
                unit = EXCLUDED.unit,
                qty = EXCLUDED.qty,
                status = EXCLUDED.status,
                started_at = EXCLUDED.started_at,
                total_sec = EXCLUDED.total_sec,
                sort_order = EXCLUDED.sort_order
        """, (
            line.get('id'), line.get('name'), line.get('colorIdx', 0),
            line.get('product', ''), line.get('tpu'), line.get('unit', 'sec'),
            line.get('qty'), line.get('status', 'idle'), line.get('startedAt'),
            line.get('totalSec', 0), i
        ))
    if lines:
        ids = [l.get('id') for l in lines]
        cur.execute("DELETE FROM factory_lines WHERE id != ALL(%s)", (ids,))
    else:
        cur.execute("DELETE FROM factory_lines")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


# History

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM factory_history ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/history', methods=['POST'])
def save_history():
    history = request.json
    conn = get_conn()
    cur = conn.cursor()
    for h in history:
        cur.execute("""
            INSERT INTO factory_history (id, product, tpu, unit, qty, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                product = EXCLUDED.product,
                tpu = EXCLUDED.tpu,
                unit = EXCLUDED.unit,
                qty = EXCLUDED.qty,
                created_at = EXCLUDED.created_at
        """, (
            h.get('id'), h.get('product', ''), h.get('tpu'),
            h.get('unit', 'sec'), h.get('qty'), h.get('createdAt', 0)
        ))
    if history:
        ids = [h.get('id') for h in history]
        cur.execute("DELETE FROM factory_history WHERE id != ALL(%s)", (ids,))
    else:
        cur.execute("DELETE FROM factory_history")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    create_tables()
    print("Factory API running at http://localhost:5050")
    app.run(port=5050, debug=False)