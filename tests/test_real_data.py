"""Reconciliation checks on the real dataset. Skipped when data/retail.db has not been built."""
import re
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "retail.db"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="run `python src/load_data.py` first")


@pytest.fixture(scope="module")
def con():
    c = sqlite3.connect(DB)
    yield c
    c.close()


def test_every_raw_row_is_accounted_for(con):
    raw = con.execute("SELECT COUNT(*) FROM raw_transactions").fetchone()[0]
    fates = pd.read_csv(ROOT / "outputs" / "csv" / "data_quality_fates.csv")
    assert fates["raw_rows"].sum() == raw


def test_clean_lines_match_independent_pandas_logic(con):
    """Recompute the cleaning in pandas with different code and compare totals."""
    raw = pd.read_sql("SELECT invoice, stock_code, quantity, unit_price, source_sheet FROM raw_transactions", con)
    first = set(raw.loc[raw.source_sheet == "Year 2009-2010", "invoice"])
    raw = raw[(raw.source_sheet == "Year 2009-2010") | ~raw.invoice.isin(first)]
    raw = raw[(raw.unit_price > 0) & raw.stock_code.str.match(r"^\d{5}")]
    is_c = raw.invoice.str.startswith("C")
    sales = raw[~is_c & ~raw.invoice.str.startswith("A") & (raw.quantity > 0)]
    canc = raw[is_c & (raw.quantity < 0)]
    sql_sales, sql_canc = con.execute(
        "SELECT SUM(CASE WHEN line_type='sale' THEN line_value END), SUM(CASE WHEN line_type='cancellation' THEN line_value END) FROM clean_lines"
    ).fetchone()
    assert sql_sales == pytest.approx((sales.quantity * sales.unit_price).sum(), rel=1e-9)
    assert sql_canc == pytest.approx((canc.quantity * canc.unit_price).abs().sum(), rel=1e-9)


def test_cancellation_classes_sum_to_total(con):
    total = con.execute("SELECT SUM(line_value) FROM clean_lines WHERE line_type='cancellation'").fetchone()[0]
    by_class = con.execute("SELECT SUM(line_value) FROM cancellation_class").fetchone()[0]
    assert by_class == pytest.approx(total)


def test_no_invalid_values_in_clean_lines(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM clean_lines WHERE unit_price <= 0 OR line_value <= 0 OR line_type IS NULL OR invoice_date IS NULL"
    ).fetchone()[0]
    assert bad == 0


def test_invoices_in_both_sheets_are_kept_once(con):
    """Invoices present in both workbook sheets must keep only the first sheet's lines."""
    both = ("SELECT DISTINCT invoice FROM raw_transactions WHERE source_sheet = 'Year 2010-2011' "
            "AND invoice IN (SELECT invoice FROM raw_transactions WHERE source_sheet = 'Year 2009-2010')")
    clean = con.execute(f"SELECT COUNT(*) FROM clean_lines WHERE invoice IN ({both})").fetchone()[0]
    sheet_a = con.execute(
        f"SELECT COUNT(*) FROM raw_transactions WHERE source_sheet = 'Year 2009-2010' AND invoice IN ({both}) "
        "AND unit_price > 0 AND stock_code GLOB '[0-9][0-9][0-9][0-9][0-9]*' AND invoice NOT LIKE 'A%' "
        "AND ((invoice LIKE 'C%' AND quantity < 0) OR (invoice NOT LIKE 'C%' AND quantity > 0))"
    ).fetchone()[0]
    assert clean == sheet_a > 0


def test_kpi_overview_is_internally_consistent():
    k = pd.read_csv(ROOT / "outputs" / "csv" / "kpi_overview.csv").iloc[0]
    parts = k.reversal_24h_gbp + k.other_cancelled_gbp + k.unmatched_gbp
    assert parts == pytest.approx(k.cancelled_gbp, abs=2)  # each figure is rounded to the pound
    assert k.headline_rate_pct == pytest.approx(100 * k.cancelled_gbp / k.gross_sales_gbp, abs=0.01)
    expected_adj = 100 * (k.other_cancelled_gbp + k.unmatched_gbp) / (k.gross_sales_gbp - k.reversal_24h_gbp)
    assert k.adjusted_rate_pct == pytest.approx(expected_adj, abs=0.01)


def test_monthly_rows_cover_the_whole_period():
    m = pd.read_csv(ROOT / "outputs" / "csv" / "monthly.csv")
    assert len(m) == 25 and m.invoice_month.is_monotonic_increasing
    assert all(re.fullmatch(r"\d{4}-\d{2}", s) for s in m.invoice_month)
