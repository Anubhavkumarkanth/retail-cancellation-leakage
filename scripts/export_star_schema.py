"""Export a Power BI star schema from data/retail.db.

Opens the database read-only and writes fact_lines, dim_date, dim_product and dim_customer as CSV.
Usage: python scripts/export_star_schema.py data/retail.db out/powerbi
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd


def export(db: Path, out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    fact = pd.read_sql(
        """SELECT l.rowid AS line_id,
                  CAST(strftime('%Y%m%d', l.invoice_date) AS INTEGER) AS date_key,
                  l.invoice, l.stock_code, l.customer_id, l.country, l.line_type, c.cancel_class,
                  l.quantity, l.unit_price, l.line_value
           FROM clean_lines l
           LEFT JOIN cancellation_class c ON c.line_id = l.rowid""",
        con,
    )
    # Stored as REAL in SQLite because pandas used NaN for missing IDs; the IDs are whole numbers.
    fact["customer_id"] = fact["customer_id"].astype("Int64")

    first, last = (pd.to_datetime(str(k), format="%Y%m%d") for k in (fact.date_key.min(), fact.date_key.max()))
    days = pd.date_range(first, last, freq="D")
    dim_date = pd.DataFrame({
        "date_key": days.strftime("%Y%m%d").astype(int), "date": days.strftime("%Y-%m-%d"),
        "year": days.year, "quarter": days.quarter, "month": days.month,
        "month_name": days.strftime("%b"), "year_month": days.strftime("%Y-%m"), "weekday": days.strftime("%a"),
    })
    # shortcut: MAX() picks one description per code when a code has several spellings; fine for labels.
    dim_product = pd.read_sql("SELECT stock_code, MAX(description) AS description FROM clean_lines GROUP BY stock_code", con)
    # A few customers appear under more than one country; the dimension keeps the one with the most lines.
    dim_customer = pd.read_sql(
        """SELECT customer_id, country FROM (
               SELECT customer_id, country,
                      ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY COUNT(*) DESC, country) AS rn
               FROM clean_lines WHERE customer_id IS NOT NULL GROUP BY customer_id, country)
           WHERE rn = 1""",
        con,
    )
    dim_customer["customer_id"] = dim_customer["customer_id"].astype("Int64")
    con.close()

    tables = {"fact_lines": fact, "dim_date": dim_date, "dim_product": dim_product, "dim_customer": dim_customer}
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return {name: len(df) for name, df in tables.items()}


if __name__ == "__main__":
    for name, rows in export(Path(sys.argv[1]), Path(sys.argv[2])).items():
        print(f"{name}: {rows:,} rows")
