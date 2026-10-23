"""Run the SQL pipeline against data/retail.db and export each named query to outputs/csv/."""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "retail.db"
SQL = ROOT / "sql"
CSV = ROOT / "outputs" / "csv"


def run(db: Path = DB, out: Path = CSV) -> dict[str, pd.DataFrame]:
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with sqlite3.connect(db) as con:
        con.executescript((SQL / "01_clean.sql").read_text())
        con.execute("CREATE INDEX IF NOT EXISTS idx_clean_cs ON clean_lines (customer_id, stock_code, line_type)")
        con.executescript((SQL / "02_classify_cancellations.sql").read_text())
        text = (SQL / "03_metrics.sql").read_text()
        for name, body in re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name: |\Z)", text, flags=re.S):
            df = pd.read_sql(body, con)
            df.to_csv(out / f"{name}.csv", index=False)
            results[name] = df
    return results


if __name__ == "__main__":
    for name, df in run().items():
        print(f"{name}: {len(df)} rows")
