"""Run the SQL pipeline against the MySQL database at DATABASE_URL and export each named query to outputs/csv/."""
import re
from pathlib import Path

import pandas as pd

from load_data import engine

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
CSV = ROOT / "outputs" / "csv"


def run_script(con, path: Path) -> None:
    """Run each ;-separated statement of a SQL file (the files keep semicolons out of comments)."""
    for stmt in path.read_text().split(";"):
        if re.sub(r"--.*", "", stmt).strip():
            con.exec_driver_sql(stmt)


def run(out: Path = CSV) -> dict[str, pd.DataFrame]:
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with engine().connect() as con:
        run_script(con, SQL / "01_clean.sql")
        con.exec_driver_sql("CREATE INDEX idx_clean_cs ON clean_lines (customer_id, stock_code, line_type)")
        run_script(con, SQL / "02_classify_cancellations.sql")
        text = (SQL / "03_metrics.sql").read_text()
        for name, body in re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name: |\Z)", text, flags=re.S):
            df = pd.read_sql(body, con)
            df.to_csv(out / f"{name}.csv", index=False)
            results[name] = df
    return results


if __name__ == "__main__":
    for name, df in run().items():
        print(f"{name}: {len(df)} rows")
