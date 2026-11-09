"""Checks that the star-schema CSVs reconcile with the MySQL tables and that
the planned DAX measures reproduce the published KPIs. Reads the database at DATABASE_URL read-only.

Run: python -m pytest tests/test_star_schema.py  (STAR_OUT may override the output folder)
"""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import inspect

HERE = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("STAR_OUT", HERE / "out" / "powerbi"))
sys.path.insert(0, str(HERE / "scripts"))
from export_star_schema import export  # noqa: E402
from load_data import engine  # noqa: E402  (export_star_schema put src/ on the path)


def _built() -> bool:
    try:
        return "DATABASE_URL" in os.environ and inspect(engine()).has_table("cancellation_class")
    except Exception:  # server not running: same as the database file not being built before
        return False


pytestmark = pytest.mark.skipif(not _built(), reason="set DATABASE_URL and run run_all.py first")


@pytest.fixture(scope="module")
def star():
    export(OUT)
    return {n: pd.read_csv(OUT / f"{n}.csv") for n in ("fact_lines", "dim_date", "dim_product", "dim_customer")}


@pytest.fixture(scope="module")
def con():
    c = engine().connect()
    c.exec_driver_sql("SET SESSION TRANSACTION READ ONLY")
    yield c
    c.close()


def test_fact_has_one_row_per_clean_line(star, con):
    assert len(star["fact_lines"]) == con.exec_driver_sql("SELECT COUNT(*) FROM clean_lines").fetchone()[0]
    assert star["fact_lines"]["line_id"].is_unique


def test_values_reconcile_by_line_type(star, con):
    got = star["fact_lines"].groupby("line_type")["line_value"].sum()
    for line_type, expected in con.exec_driver_sql("SELECT line_type, SUM(line_value) FROM clean_lines GROUP BY 1"):
        assert got[line_type] == pytest.approx(expected, rel=1e-9)


def test_values_reconcile_by_cancel_class(star, con):
    got = star["fact_lines"].groupby("cancel_class")["line_value"].sum()
    for cls, expected in con.exec_driver_sql("SELECT cancel_class, SUM(line_value) FROM cancellation_class GROUP BY 1"):
        assert got[cls] == pytest.approx(expected, rel=1e-9)
    assert star["fact_lines"].loc[star["fact_lines"].line_type == "sale", "cancel_class"].isna().all()


def test_every_fact_key_exists_in_its_dimension(star):
    f = star["fact_lines"]
    assert star["dim_date"]["date_key"].is_unique and set(f.date_key) <= set(star["dim_date"].date_key)
    assert star["dim_product"]["stock_code"].is_unique and set(f.stock_code) <= set(star["dim_product"].stock_code)
    known = set(star["dim_customer"].customer_id)
    assert star["dim_customer"]["customer_id"].is_unique and set(f.customer_id.dropna()) <= known


def test_customer_ids_are_whole_numbers(star):
    ids = star["fact_lines"]["customer_id"].dropna()
    assert (ids == ids.round()).all()


def test_dax_measures_reproduce_published_kpis(star):
    """Same arithmetic as the DAX in docs/powerbi-guide.md."""
    f = star["fact_lines"]
    gross = f.loc[f.line_type == "sale", "line_value"].sum()
    cancelled = f.loc[f.line_type == "cancellation", "line_value"].sum()
    reversals = f.loc[f.cancel_class == "reversal_24h", "line_value"].sum()
    assert round(100 * cancelled / gross, 2) == 3.65
    assert round(100 * (cancelled - reversals) / (gross - reversals), 2) == 1.88
    assert round(100 * reversals / cancelled, 1) == 49.5
