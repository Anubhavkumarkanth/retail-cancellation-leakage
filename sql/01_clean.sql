-- Cleaning rules, each one justified by profiling the raw table (see README "Data quality").
-- Output: table clean_lines, one row per usable product line, tagged 'sale' or 'cancellation'.

DROP TABLE IF EXISTS clean_lines;

CREATE TABLE clean_lines AS
WITH first_sheet_invoices AS (
    -- Rule 1: the two workbook sheets overlap on 2010-12-01..2010-12-09. Keep each invoice once,
    -- from the earlier sheet.
    SELECT DISTINCT invoice FROM raw_transactions WHERE source_sheet = 'Year 2009-2010'
),
deduped AS (
    SELECT r.*
    FROM raw_transactions r
    WHERE r.source_sheet = 'Year 2009-2010'
       OR r.invoice NOT IN (SELECT invoice FROM first_sheet_invoices)
)
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    unit_price,
    customer_id,
    country,
    invoice_date,
    substr(invoice_date, 1, 7)                       AS invoice_month,
    CASE
        WHEN invoice LIKE 'C%' AND quantity < 0 THEN 'cancellation'
        WHEN invoice NOT LIKE 'C%' AND invoice NOT LIKE 'A%' AND quantity > 0 THEN 'sale'
    END                                              AS line_type,
    ABS(quantity * unit_price)                       AS line_value
FROM deduped
WHERE unit_price > 0                                  -- Rule 2: drop zero/negative-price rows (stock write-offs, bad-debt adjustments)
  AND stock_code GLOB '[0-9][0-9][0-9][0-9][0-9]*'    -- Rule 3: real products only (drops POST, DOT, M, D, BANK CHARGES, AMAZONFEE, gift vouchers, tests)
  AND (
        (invoice LIKE 'C%' AND quantity < 0)          -- Rule 4: cancellations are 'C' invoices with negative quantity
     OR (invoice NOT LIKE 'C%' AND invoice NOT LIKE 'A%' AND quantity > 0)
      );

CREATE INDEX idx_clean_type_month ON clean_lines (line_type, invoice_month);
CREATE INDEX idx_clean_customer   ON clean_lines (customer_id);
CREATE INDEX idx_clean_stock      ON clean_lines (stock_code);
