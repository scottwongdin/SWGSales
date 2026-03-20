import sqlite3
import psycopg2
import sys
import os

# Allow passing a config file as argument e.g. python migrate_to_supabase.py config_test
config_module = sys.argv[1] if len(sys.argv) > 1 else 'config'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
config = __import__(config_module)
DB_HOST = config.DB_HOST
DB_NAME = config.DB_NAME
DB_USER = config.DB_USER
DB_PASSWORD = config.DB_PASSWORD
DB_PORT = config.DB_PORT

SQLITE_PATH = r"C:\Users\scott\OneDrive\Documents\SWGSales\swg.db"

def get_pg():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, port=DB_PORT
    )

def get_sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_pg_tables(pg):
    cur = pg.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            mail_id SERIAL PRIMARY KEY,
            filename TEXT UNIQUE,
            body TEXT,
            datetime TEXT,
            sold_date TEXT,
            sold_time TEXT,
            product TEXT,
            price INTEGER,
            customer TEXT,
            crate_size INTEGER,
            vendor TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            product_id SERIAL PRIMARY KEY,
            product TEXT,
            total_units INTEGER,
            vendor TEXT,
            restock INTEGER DEFAULT -1,
            UNIQUE (product, total_units, vendor)
        )
    """)

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

    pg.commit()
    print("Tables created in Supabase.")

def migrate_sales(sqlite, pg):
    cur_sl = sqlite.cursor()
    cur_pg = pg.cursor()
    rows = cur_sl.execute("SELECT * FROM sales").fetchall()
    count = 0
    for row in rows:
        try:
            cur_pg.execute("""
                INSERT INTO sales (filename, body, datetime, sold_date, sold_time, product, price, customer, crate_size, vendor)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (filename) DO NOTHING
            """, (row['filename'], row['body'], row['datetime'], row['sold_date'],
                  row['sold_time'], row['product'], row['price'], row['customer'],
                  row['crate_size'], row['vendor']))
            count += 1
        except Exception as e:
            print(f"  [WARN] Skipped sales row: {e}")
    pg.commit()
    print(f"Migrated {count} sales records.")

def migrate_inventory(sqlite, pg):
    cur_sl = sqlite.cursor()
    cur_pg = pg.cursor()
    rows = cur_sl.execute("SELECT * FROM inventory").fetchall()
    count = 0
    for row in rows:
        try:
            cur_pg.execute("""
                INSERT INTO inventory (product, total_units, vendor, restock)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product, total_units, vendor) DO NOTHING
            """, (row['product'], row['total_units'], row['vendor'], row['restock']))
            count += 1
        except Exception as e:
            print(f"  [WARN] Skipped inventory row: {e}")
    pg.commit()
    print(f"Migrated {count} inventory records.")

def migrate_factory_lines(sqlite, pg):
    cur_sl = sqlite.cursor()
    cur_pg = pg.cursor()
    try:
        rows = cur_sl.execute("SELECT * FROM factory_lines").fetchall()
        count = 0
        for row in rows:
            try:
                cur_pg.execute("""
                    INSERT INTO factory_lines (id, name, color_idx, product, tpu, unit, qty, status, started_at, total_sec, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (row['id'], row['name'], row['color_idx'], row['product'],
                      row['tpu'], row['unit'], row['qty'], row['status'],
                      row['started_at'], row['total_sec'], row['sort_order']))
                count += 1
            except Exception as e:
                print(f"  [WARN] Skipped factory_lines row: {e}")
        pg.commit()
        print(f"Migrated {count} factory line records.")
    except Exception as e:
        print(f"  [INFO] No factory_lines table in SQLite: {e}")

def migrate_factory_history(sqlite, pg):
    cur_sl = sqlite.cursor()
    cur_pg = pg.cursor()
    try:
        rows = cur_sl.execute("SELECT * FROM factory_history").fetchall()
        count = 0
        for row in rows:
            try:
                cur_pg.execute("""
                    INSERT INTO factory_history (id, product, tpu, unit, qty, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (row['id'], row['product'], row['tpu'], row['unit'],
                      row['qty'], row['created_at']))
                count += 1
            except Exception as e:
                print(f"  [WARN] Skipped factory_history row: {e}")
        pg.commit()
        print(f"Migrated {count} factory history records.")
    except Exception as e:
        print(f"  [INFO] No factory_history table in SQLite: {e}")

if __name__ == '__main__':
    print("Connecting to Supabase...")
    pg = get_pg()
    print("Connected!")

    print("Connecting to SQLite...")
    sqlite = get_sqlite()
    print("Connected!")

    print("\nCreating tables in Supabase...")
    create_pg_tables(pg)

    print("\nMigrating data...")
    migrate_sales(sqlite, pg)
    migrate_inventory(sqlite, pg)
    migrate_factory_lines(sqlite, pg)
    migrate_factory_history(sqlite, pg)

    sqlite.close()
    pg.close()

    print("\nMigration complete!")