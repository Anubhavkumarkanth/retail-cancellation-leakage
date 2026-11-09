"""SQL logic checked on a tiny hand-built dataset where every expected value is known."""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
sys.path.insert(0, str(ROOT / "src"))
from load_data import engine, write_raw  # noqa: E402
from run_sql import run_script  # noqa: E402
A, B = "Year 2009-2010", "Year 2010-2011"

ROWS = [
    # invoice, stock, desc, qty, date, price, cust, country, sheet
    ("1001", "10001", "WIDGET", 5, "2010-01-01 10:00:00", 2.0, 1.0, "United Kingdom", A),
    ("C1001", "10001", "WIDGET", -5, "2010-01-01 11:00:00", 2.0, 1.0, "United Kingdom", A),   # same-day reversal
    ("1002", "10002", "GADGET", 3, "2010-01-01 10:00:00", 1.0, 1.0, "United Kingdom", A),
    ("C1002", "10002", "GADGET", -1, "2010-02-01 10:00:00", 1.0, 1.0, "United Kingdom", A),   # later partial return
    ("1003", "POST", "POSTAGE", 1, "2010-01-01 10:00:00", 9.0, 1.0, "United Kingdom", A),     # non-product
    ("1004", "10003", "FREEBIE", 1, "2010-01-01 10:00:00", 0.0, 1.0, "United Kingdom", A),    # zero price
    ("A1005", "10004", "BAD DEBT", 1, "2010-01-01 10:00:00", 4.0, None, "United Kingdom", A),  # adjustment invoice
    ("1006", "10005", "OVERLAP", 2, "2010-12-05 10:00:00", 5.0, 2.0, "France", A),
    ("1006", "10005", "OVERLAP", 2, "2010-12-05 10:00:00", 5.0, 2.0, "France", B),             # duplicate from 2nd sheet
    ("C1007", "10006", "ANON", -2, "2010-03-01 10:00:00", 3.0, None, "Spain", A),              # cancellation, no customer
    ("1008", "10007", "WRITEOFF", -4, "2010-03-01 10:00:00", 1.0, None, "Spain", A),           # negative qty, not a C invoice
]


@pytest.fixture()
def con():
    url = os.environ["TEST_DATABASE_URL"]
    # The fixture drops and rebuilds the pipeline tables, so it must never point at the real data.
    assert url != os.environ.get("DATABASE_URL"), "TEST_DATABASE_URL must be a separate, throwaway database"
    eng = engine(url)
    df = pd.DataFrame(ROWS, columns=["invoice", "stock_code", "description", "quantity", "invoice_date",
                                     "unit_price", "customer_id", "country", "source_sheet"])
    write_raw(df, eng)
    c = eng.connect()
    run_script(c, SQL / "01_clean.sql")
    run_script(c, SQL / "02_classify_cancellations.sql")
    yield c
    c.close()
    eng.dispose()


def test_cleaning_keeps_only_product_sales_and_cancellations(con):
    kept = {r[0] for r in con.exec_driver_sql("SELECT invoice FROM clean_lines")}
    assert kept == {"1001", "C1001", "1002", "C1002", "1006", "C1007"}


def test_sheet_overlap_is_deduplicated(con):
    assert con.exec_driver_sql("SELECT COUNT(*) FROM clean_lines WHERE invoice = '1006'").fetchone()[0] == 1


def test_line_value_is_absolute_quantity_times_price(con):
    assert con.exec_driver_sql("SELECT line_value FROM clean_lines WHERE invoice = 'C1001'").fetchone()[0] == 10.0


def test_cancellation_classes(con):
    classes = dict(con.exec_driver_sql("SELECT invoice, cancel_class FROM cancellation_class").fetchall())
    assert classes == {"C1001": "reversal_24h", "C1002": "other", "C1007": "unmatched_no_customer"}


def test_reversal_requires_matching_quantity(con):
    con.exec_driver_sql("UPDATE clean_lines SET quantity = -4 WHERE invoice = 'C1001'")
    con.exec_driver_sql("DROP TABLE cancellation_class")
    run_script(con, SQL / "02_classify_cancellations.sql")
    assert con.exec_driver_sql("SELECT cancel_class FROM cancellation_class WHERE invoice = 'C1001'").fetchone()[0] == "other"


def test_cancellation_must_not_precede_the_sale(con):
    con.exec_driver_sql("UPDATE clean_lines SET invoice_date = '2009-12-31 09:00:00' WHERE invoice = 'C1001'")
    con.exec_driver_sql("DROP TABLE cancellation_class")
    run_script(con, SQL / "02_classify_cancellations.sql")
    assert con.exec_driver_sql("SELECT cancel_class FROM cancellation_class WHERE invoice = 'C1001'").fetchone()[0] == "other"


@pytest.mark.parametrize("cancelled_at, expected", [
    ("2010-01-02 09:59:00", "reversal_24h"),  # 23 h 59 min after the sale at 2010-01-01 10:00
    ("2010-01-02 10:00:00", "reversal_24h"),  # exactly 24 h: the rule is "at most 24 hours"
    ("2010-01-02 10:01:00", "other"),         # 24 h 1 min: outside the window
])
def test_reversal_window_is_at_most_24_hours(con, cancelled_at, expected):
    con.exec_driver_sql("UPDATE clean_lines SET invoice_date = %s WHERE invoice = 'C1001'", (cancelled_at,))
    con.exec_driver_sql("DROP TABLE cancellation_class")
    run_script(con, SQL / "02_classify_cancellations.sql")
    assert con.exec_driver_sql("SELECT cancel_class FROM cancellation_class WHERE invoice = 'C1001'").fetchone()[0] == expected
