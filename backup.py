import psycopg2
import csv
import os
import sys
from datetime import datetime

# Allow passing a config file as argument e.g. python backup.py config_test
config_module = sys.argv[1] if len(sys.argv) > 1 else 'config'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
config = __import__(config_module)
DB_HOST = config.DB_HOST
DB_NAME = config.DB_NAME
DB_USER = config.DB_USER
DB_PASSWORD = config.DB_PASSWORD
DB_PORT = config.DB_PORT

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")

TABLES = [
    "sales",
    "inventory",
    "factory_lines",
    "factory_history"
]


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, port=DB_PORT
    )


def backup_table(cur, table, backup_folder):
    """Export a single table to a CSV file."""
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    filepath = os.path.join(backup_folder, f"{table}.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  ✓ {table} — {len(rows)} rows → {filepath}")
    return len(rows)


def run_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = os.path.join(BACKUP_DIR, timestamp)
    os.makedirs(backup_folder, exist_ok=True)

    print(f"=====================================")
    print(f"  SWG Crafter Database Backup")
    print(f"=====================================")
    print(f"  Timestamp : {timestamp}")
    print(f"  Folder    : {backup_folder}")
    print()

    try:
        conn = get_conn()
        cur = conn.cursor()
        print("Connected to Supabase.")
        print()

        total_rows = 0
        for table in TABLES:
            try:
                count = backup_table(cur, table, backup_folder)
                total_rows += count
            except Exception as e:
                print(f"  ✗ {table} — ERROR: {e}")

        cur.close()
        conn.close()

        print()
        print(f"Backup complete! {total_rows} total rows saved to:")
        print(f"  {backup_folder}")

    except Exception as e:
        print(f"Failed to connect to Supabase: {e}")


if __name__ == "__main__":
    run_backup()