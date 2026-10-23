"""Load the UCI Online Retail II workbook into a local SQLite database (raw table, unmodified)."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"
DB = ROOT / "data" / "retail.db"

COLS = {
    "Invoice": "invoice", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "Price": "unit_price",
    "Customer ID": "customer_id", "Country": "country",
}


def main() -> int:
    if not XLSX.exists():
        print(f"Missing {XLSX}. Run: python scripts/download_data.py", file=sys.stderr)
        return 1
    frames = []
    for sheet in ("Year 2009-2010", "Year 2010-2011"):
        df = pd.read_excel(XLSX, sheet_name=sheet, dtype={"Invoice": str, "StockCode": str})
        df["source_sheet"] = sheet
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True).rename(columns=COLS)
    raw["invoice_date"] = pd.to_datetime(raw["invoice_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        raw.to_sql("raw_transactions", con, index=False)
    print(f"Loaded {len(raw):,} rows into {DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
