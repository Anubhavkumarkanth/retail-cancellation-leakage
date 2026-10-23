"""SQL logic checked on a tiny hand-built dataset where every expected value is known."""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

SQL = Path(__file__).resolve().parents[1] / "sql"
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
    c = sqlite3.connect(":memory:")
    df = pd.DataFrame(ROWS, columns=["invoice", "stock_code", "description", "quantity", "invoice_date",
                                     "unit_price", "customer_id", "country", "source_sheet"])
    df.to_sql("raw_transactions", c, index=False)
    c.executescript((SQL / "01_clean.sql").read_text())
    c.executescript((SQL / "02_classify_cancellations.sql").read_text())
    yield c
    c.close()


def test_cleaning_keeps_only_product_sales_and_cancellations(con):
    kept = {r[0] for r in con.execute("SELECT invoice FROM clean_lines")}
    assert kept == {"1001", "C1001", "1002", "C1002", "1006", "C1007"}


def test_sheet_overlap_is_deduplicated(con):
    assert con.execute("SELECT COUNT(*) FROM clean_lines WHERE invoice = '1006'").fetchone()[0] == 1


def test_line_value_is_absolute_quantity_times_price(con):
    assert con.execute("SELECT line_value FROM clean_lines WHERE invoice = 'C1001'").fetchone()[0] == 10.0


def test_cancellation_classes(con):
    classes = dict(con.execute("SELECT invoice, cancel_class FROM cancellation_class"))
    assert classes == {"C1001": "reversal_24h", "C1002": "other", "C1007": "unmatched_no_customer"}


def test_reversal_requires_matching_quantity(con):
    con.execute("UPDATE clean_lines SET quantity = -4 WHERE invoice = 'C1001'")
    con.execute("DROP TABLE cancellation_class")
    con.executescript((SQL / "02_classify_cancellations.sql").read_text())
    assert con.execute("SELECT cancel_class FROM cancellation_class WHERE invoice = 'C1001'").fetchone()[0] == "other"


def test_cancellation_must_not_precede_the_sale(con):
    con.execute("UPDATE clean_lines SET invoice_date = '2009-12-31 09:00:00' WHERE invoice = 'C1001'")
    con.execute("DROP TABLE cancellation_class")
    con.executescript((SQL / "02_classify_cancellations.sql").read_text())
    assert con.execute("SELECT cancel_class FROM cancellation_class WHERE invoice = 'C1001'").fetchone()[0] == "other"
