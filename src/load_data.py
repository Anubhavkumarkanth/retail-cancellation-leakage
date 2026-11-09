"""Load the UCI Online Retail II workbook into the MySQL database at DATABASE_URL (raw table, unmodified)."""
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import VARCHAR

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"

COLS = {
    "Invoice": "invoice", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "Price": "unit_price",
    "Customer ID": "customer_id", "Country": "country",
}
# Binary collation matches text exactly and case-sensitively (e.g. stock codes 85123A and 85123a stay apart).
TEXT = VARCHAR(255, charset="utf8mb4", collation="utf8mb4_0900_bin")
TEXT_COLS = ("invoice", "stock_code", "description", "invoice_date", "country", "source_sheet")


def engine(url: str | None = None):
    """One connection setup for every script and test: each statement commits as it runs."""
    # no_parameters: a query sent without parameters reaches MySQL as written, so LIKE 'C%' needs no escaping.
    return create_engine(url or os.environ["DATABASE_URL"], isolation_level="AUTOCOMMIT",
                         execution_options={"no_parameters": True})


def write_raw(df: pd.DataFrame, eng) -> None:
    df.to_sql("raw_transactions", eng, index=False, if_exists="replace", chunksize=20_000,
              dtype={c: TEXT for c in TEXT_COLS if c in df.columns})


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
    write_raw(raw, engine())
    print(f"Loaded {len(raw):,} rows into raw_transactions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
