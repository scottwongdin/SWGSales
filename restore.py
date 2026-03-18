import psycopg2
import csv
import os
import sys
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

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


def list_backups():
    """List all available backup folders."""
    if not os.path.isdir(BACKUP_DIR):
        print("No backups folder found.")
        return []
    folders = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if os.path.isdir(os.path.join(BACKUP_DIR, f))
    ], reverse=True)
    return folders


def restore_table(cur, conn, table, backup_folder):
    """Restore a single table from a CSV file."""
    filepath = os.path.join(backup_folder, f"{table}.csv")
    if not os.path.exists(filepath):
        print(f"  ✗ {table} — CSV file not found, skipping.")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"  - {table} — empty file, skipping.")
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(columns)

    # Clear existing data
    cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")

    # Insert rows
    count = 0
    for row in rows:
        values = []
        for col in columns:
            val = row[col]
            values.append(None if val == '' else val)
        cur.execute(
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
            values
        )
        count += 1

    conn.commit()
    print(f"  ✓ {table} — {count} rows restored")
    return count


def run_restore(backup_folder):
    print(f"=====================================")
    print(f"  SWG Crafter Database Restore")
    print(f"=====================================")
    print(f"  Restoring from: {backup_folder}")
    print()

    confirm = input("⚠ WARNING: This will overwrite all current data. Type YES to continue: ")
    if confirm.strip() != "YES":
        print("Restore cancelled.")
        return

    print()

    try:
        conn = get_conn()
        cur = conn.cursor()
        print("Connected to Supabase.")
        print()

        total_rows = 0
        for table in TABLES:
            try:
                count = restore_table(cur, conn, table, backup_folder)
                total_rows += count
            except Exception as e:
                print(f"  ✗ {table} — ERROR: {e}")
                conn.rollback()

        cur.close()
        conn.close()

        print()
        print(f"Restore complete! {total_rows} total rows restored.")

    except Exception as e:
        print(f"Failed to connect to Supabase: {e}")


if __name__ == "__main__":
    backups = list_backups()

    if not backups:
        print("No backups found in the backups folder.")
        sys.exit(1)

    print("=====================================")
    print("  Available Backups")
    print("=====================================")
    for i, folder in enumerate(backups):
        print(f"  [{i+1}] {folder}")

    print()
    choice = input(f"Select a backup to restore (1-{len(backups)}): ").strip()

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(backups):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        sys.exit(1)

    selected = os.path.join(BACKUP_DIR, backups[idx])
    run_restore(selected)
