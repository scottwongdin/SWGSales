import os
import shutil
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.txt")


def log(message):
    """Print message to console and append to log file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, port=DB_PORT
    )


def extract_sold_datetime(body):
    """Extract the TIMESTAMP line from the mail body and convert to PST date and time strings."""
    match = re.search(r"^TIMESTAMP:\s*(\d+)", body, re.MULTILINE | re.IGNORECASE)
    if match:
        unix_ts = int(match.group(1))
        pst = ZoneInfo("America/Los_Angeles")
        dt = datetime.fromtimestamp(unix_ts, tz=pst)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
    return None, None


def extract_vendor(body):
    """Identify which vendor sold the item — Cafe Eponine or Brasserie Eponine."""
    if "cafe eponine" in body.lower():
        return "Cafe Eponine"
    elif "brasserie eponine" in body.lower():
        return "Brasserie Eponine"
    return "Other"


def extract_quantity(body):
    """Extract the item count — number between 1 and 100 immediately before the word 'to'."""
    match = re.search(r"\b([1-9][0-9]?|100)\s+to\s+.+?\s+for\s+[\d,]+\s+credits", body, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1


def extract_customer(body):
    """Extract the customer name — text between 'to' and 'for' on the Vendor line."""
    match = re.search(r"\bto\s+(.+?)\s+for\s+[\d,]+\s+credits", body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_price(body):
    """Extract the price from the Vendor line — the number immediately before the word 'credits'."""
    match = re.search(r"([\d,]+)\s+credits", body, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_product(body):
    """Extract the product name from the Vendor line.
    Handles two formats:
    1. Pipe format: text between first and second pipe
    2. Simple format: text between 'sold' and 'to'
    """
    match = re.search(r"^Vendor:.*?\|(.+?)\|", body, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"\bsold\s+(.+?)\s+to\b", body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def file_already_imported(cur, filename):
    """Check if a file has already been imported by filename."""
    cur.execute("SELECT 1 FROM sales WHERE filename = %s", (filename,))
    return cur.fetchone() is not None


def import_mail_files(directory):
    """Read all .mail files from a directory and insert into PostgreSQL."""
    if not os.path.isdir(directory):
        log(f"Error: '{directory}' is not a valid directory.")
        return

    conn = get_conn()
    cur = conn.cursor()

    files = [f for f in os.listdir(directory) if f.endswith(".mail")]

    if not files:
        log(f"No .mail files found in '{directory}'.")
        conn.close()
        return

    imported = 0
    skipped = 0
    moved = 0
    move_warnings = 0

    processed_dir = os.path.join(directory, "processed")

    for filename in files:
        filepath = os.path.join(directory, filename)

        if file_already_imported(cur, filename):
            skipped += 1
        else:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                body = f.read()

            # Only import mails from SWG.Restoration.Auctioner
            if "swg.restoration.auctioner" not in body.lower():
                log(f"  [SKIP]   {filename} (not an Auctioner message)")
                skipped += 1
            elif "you have won the auction" in body.lower():
                log(f"  [SKIP]   {filename} (auction won message)")
                skipped += 1
            elif "the offer took place" in body.lower():
                log(f"  [SKIP]   {filename} (offer took place message)")
                skipped += 1
            elif "cafe eponine" not in body.lower() and "brasserie eponine" not in body.lower():
                log(f"  [SKIP]   {filename} (not from Cafe Eponine or Brasserie Eponine)")
                skipped += 1
            else:
                sold_date, sold_time = extract_sold_datetime(body)
                product = extract_product(body)
                price = extract_price(body)
                customer = extract_customer(body)
                vendor = extract_vendor(body)
                # If the product is a supplement, always set crate_size to 1
                if product and "supplement" in product.lower():
                    crate_size = 1
                else:
                    crate_size = extract_quantity(body)
                cur.execute("""
                    INSERT INTO sales (filename, body, datetime, sold_date, sold_time, product, price, customer, crate_size, vendor)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (filename) DO NOTHING
                """, (filename, body, datetime.now().isoformat(), sold_date, sold_time, product, price, customer, crate_size, vendor))
                # Decrease total_units by crate_size for matching product and vendor
                cur.execute("""
                    UPDATE inventory SET total_units = total_units - %s
                    WHERE product = %s AND vendor = %s
                """, (crate_size, product, vendor))
                # If no matching row was found, insert a new row with total_units = -crate_size
                if cur.rowcount == 0:
                    cur.execute("""
                        INSERT INTO inventory (product, total_units, vendor, restock)
                        VALUES (%s, %s, %s, -1)
                        ON CONFLICT (product, total_units, vendor) DO NOTHING
                    """, (product, -crate_size, vendor))
                    log(f"  [INVENTORY] No inventory found — inserted new row with total_units -{crate_size}")
                    log(f"              filename  : {filename}")
                    log(f"              product   : {product}")
                    log(f"              crate_size: {crate_size}")
                    log(f"              vendor    : {vendor}")
                imported += 1

        # Move file to /processed subdirectory — always, regardless of import status
        if not os.path.isdir(processed_dir):
            log(f"  [WARN]   Could not move '{filename}' — 'processed' directory does not exist.")
            move_warnings += 1
        else:
            dest = os.path.join(processed_dir, filename)
            shutil.move(filepath, dest)
            moved += 1

    conn.commit()
    cur.close()
    conn.close()

    log(f"\nDone! {imported} imported, {skipped} skipped, {moved} moved to 'processed/'.")
    if move_warnings:
        log(f"Warning: {move_warnings} file(s) could not be moved — create a 'processed' folder in '{directory}' to enable moving.")


if __name__ == "__main__":
    MAIL_DIR = r"C:\SWG Restoration\x64\profiles\philosophy\Restoration\mail_Eponine N'tarra"
    import_mail_files(MAIL_DIR)