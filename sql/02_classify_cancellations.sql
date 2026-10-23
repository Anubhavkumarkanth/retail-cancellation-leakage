-- Split cancellations into "same-day reversals" (an order entered and cancelled within 24h with the
-- identical quantity, i.e. an order-entry correction) and "other" (everything else).
-- Without this split, two reversed bulk orders distort every headline KPI (see README, finding 1).

DROP TABLE IF EXISTS cancellation_class;

CREATE TABLE cancellation_class AS
SELECT
    c.rowid                                        AS line_id,
    c.invoice, c.invoice_date, c.invoice_month, c.customer_id, c.country,
    c.stock_code, c.description, c.quantity, c.line_value,
    CASE
        WHEN c.customer_id IS NULL THEN 'unmatched_no_customer'
        WHEN EXISTS (
            SELECT 1 FROM clean_lines s
            WHERE s.line_type   = 'sale'
              AND s.customer_id = c.customer_id
              AND s.stock_code  = c.stock_code
              AND s.quantity    = -c.quantity
              AND s.invoice_date <= c.invoice_date
              AND julianday(c.invoice_date) - julianday(s.invoice_date) <= 1.0
        ) THEN 'reversal_24h'
        ELSE 'other'
    END                                            AS cancel_class
FROM clean_lines c
WHERE c.line_type = 'cancellation';

CREATE INDEX idx_cc_class ON cancellation_class (cancel_class);
