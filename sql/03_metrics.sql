-- Each "-- name: x" block is exported to outputs/csv/x.csv by src/run_sql.py.
-- Value = quantity * unit_price in GBP. "other" cancellations exclude same-day reversals (see 02).

-- name: kpi_overview
WITH s AS (
    SELECT SUM(line_value) AS gross, SUM(CASE WHEN customer_id IS NOT NULL THEN line_value END) AS gross_identified
    FROM clean_lines WHERE line_type = 'sale'
), c AS (
    SELECT SUM(line_value) AS cancelled,
           SUM(CASE WHEN cancel_class = 'reversal_24h' THEN line_value END) AS reversal,
           SUM(CASE WHEN cancel_class = 'other' THEN line_value END)        AS other,
           SUM(CASE WHEN cancel_class = 'unmatched_no_customer' THEN line_value END) AS unmatched
    FROM cancellation_class
)
SELECT
    ROUND(gross, 0)                                   AS gross_sales_gbp,
    ROUND(cancelled, 0)                               AS cancelled_gbp,
    ROUND(100.0 * cancelled / gross, 2)               AS headline_rate_pct,
    ROUND(reversal, 0)                                AS reversal_24h_gbp,
    ROUND(other, 0)                                   AS other_cancelled_gbp,
    ROUND(unmatched, 0)                               AS unmatched_gbp,
    ROUND(100.0 * reversal / cancelled, 1)            AS reversal_share_of_cancelled_pct,
    ROUND(100.0 * (other + unmatched) / (gross - reversal), 2) AS adjusted_rate_pct
FROM s, c;

-- name: monthly
SELECT m.invoice_month,
       ROUND(m.gross, 0) AS gross_gbp,
       ROUND(COALESCE(c.reversal, 0), 0) AS reversal_gbp,
       ROUND(COALESCE(c.other, 0) + COALESCE(c.unmatched, 0), 0) AS other_gbp,
       ROUND(100.0 * (COALESCE(c.reversal, 0) + COALESCE(c.other, 0) + COALESCE(c.unmatched, 0)) / m.gross, 2) AS headline_rate_pct,
       ROUND(100.0 * (COALESCE(c.other, 0) + COALESCE(c.unmatched, 0)) / (m.gross - COALESCE(c.reversal, 0)), 2) AS adjusted_rate_pct
FROM (SELECT invoice_month, SUM(line_value) AS gross FROM clean_lines WHERE line_type = 'sale' GROUP BY 1) m
LEFT JOIN (
    SELECT invoice_month,
           SUM(CASE WHEN cancel_class = 'reversal_24h' THEN line_value END) AS reversal,
           SUM(CASE WHEN cancel_class = 'other' THEN line_value END) AS other,
           SUM(CASE WHEN cancel_class = 'unmatched_no_customer' THEN line_value END) AS unmatched
    FROM cancellation_class GROUP BY 1) c USING (invoice_month)
ORDER BY m.invoice_month;

-- name: country
SELECT s.country,
       cu.customers,
       ROUND(s.gross, 0)                                              AS gross_gbp,
       ROUND(COALESCE(c.other, 0), 0)                                 AS other_cancelled_gbp,
       ROUND(100.0 * COALESCE(c.other, 0) / (s.gross - COALESCE(c.reversal, 0)), 2) AS adjusted_rate_pct
FROM (SELECT country, SUM(line_value) AS gross FROM clean_lines WHERE line_type = 'sale' GROUP BY 1) s
JOIN (SELECT country, COUNT(DISTINCT customer_id) AS customers FROM clean_lines WHERE line_type = 'sale' GROUP BY 1) cu USING (country)
LEFT JOIN (SELECT country,
                  SUM(CASE WHEN cancel_class IN ('other', 'unmatched_no_customer') THEN line_value END) AS other,
                  SUM(CASE WHEN cancel_class = 'reversal_24h' THEN line_value END) AS reversal
           FROM cancellation_class GROUP BY 1) c USING (country)
WHERE s.gross >= 50000
ORDER BY other_cancelled_gbp DESC;

-- name: sku_top_cancelled
WITH sales AS (
    SELECT stock_code, SUM(line_value) AS sales_gbp FROM clean_lines WHERE line_type = 'sale' GROUP BY 1
)
SELECT c.stock_code, MAX(c.description) AS description,
       ROUND(SUM(c.line_value), 0) AS other_cancelled_gbp,
       ROUND(s.sales_gbp, 0) AS sales_gbp,
       ROUND(100.0 * SUM(c.line_value) / s.sales_gbp, 1) AS rate_pct
FROM cancellation_class c
JOIN sales s USING (stock_code)
WHERE c.cancel_class IN ('other', 'unmatched_no_customer')
GROUP BY c.stock_code
ORDER BY other_cancelled_gbp DESC
LIMIT 15;

-- name: sku_concentration
WITH per_sku AS (
    SELECT stock_code, SUM(line_value) AS v
    FROM cancellation_class WHERE cancel_class IN ('other', 'unmatched_no_customer') GROUP BY 1
), ranked AS (
    SELECT v, ROW_NUMBER() OVER (ORDER BY v DESC) AS rn, COUNT(*) OVER () AS n,
           SUM(v) OVER (ORDER BY v DESC) AS running, SUM(v) OVER () AS total
    FROM per_sku
)
SELECT MAX(n) AS skus_with_other_cancellations,
       ROUND(MAX(CASE WHEN rn <= 0.05 * n THEN running END) / MAX(total) * 100, 1) AS top5pct_skus_share_pct,
       ROUND(MAX(CASE WHEN rn <= 0.20 * n THEN running END) / MAX(total) * 100, 1) AS top20pct_skus_share_pct
FROM ranked;

-- name: customer_cancel_frequency
WITH per_cust AS (
    SELECT customer_id,
           COUNT(DISTINCT invoice) AS cancel_invoices,
           SUM(line_value)         AS other_gbp
    FROM cancellation_class WHERE cancel_class = 'other' GROUP BY 1
), buyers AS (
    SELECT customer_id, COUNT(DISTINCT invoice) AS order_invoices, SUM(line_value) AS spend
    FROM clean_lines WHERE line_type = 'sale' AND customer_id IS NOT NULL GROUP BY 1
), banded AS (
    SELECT b.customer_id, b.spend, COALESCE(p.other_gbp, 0) AS other_gbp,
           CASE WHEN COALESCE(p.cancel_invoices, 0) = 0 THEN '0'
                WHEN p.cancel_invoices = 1 THEN '1'
                WHEN p.cancel_invoices <= 4 THEN '2-4'
                ELSE '5+' END AS cancel_invoice_band
    FROM buyers b LEFT JOIN per_cust p USING (customer_id)
)
SELECT cancel_invoice_band,
       COUNT(*) AS customers,
       ROUND(SUM(spend), 0) AS spend_gbp,
       ROUND(SUM(other_gbp), 0) AS other_cancelled_gbp,
       ROUND(100.0 * SUM(other_gbp) / SUM(spend), 2) AS rate_pct
FROM banded
GROUP BY cancel_invoice_band
ORDER BY CASE cancel_invoice_band WHEN '0' THEN 0 WHEN '1' THEN 1 WHEN '2-4' THEN 2 ELSE 3 END;

-- name: customer_level
SELECT b.customer_id, b.country, b.orders, ROUND(b.spend, 2) AS spend_gbp,
       COALESCE(p.cancel_invoices, 0) AS cancel_invoices,
       ROUND(COALESCE(p.other_gbp, 0), 2) AS other_cancelled_gbp
FROM (SELECT customer_id, MAX(country) AS country, COUNT(DISTINCT invoice) AS orders, SUM(line_value) AS spend
      FROM clean_lines WHERE line_type = 'sale' AND customer_id IS NOT NULL GROUP BY 1) b
LEFT JOIN (SELECT customer_id, COUNT(DISTINCT invoice) AS cancel_invoices, SUM(line_value) AS other_gbp
           FROM cancellation_class WHERE cancel_class = 'other' GROUP BY 1) p USING (customer_id);

-- name: data_quality_fates
SELECT CASE
         WHEN source_sheet = 'Year 2010-2011' AND invoice IN (SELECT invoice FROM raw_transactions WHERE source_sheet = 'Year 2009-2010') THEN '1 duplicate (sheet overlap)'
         WHEN unit_price <= 0 THEN '2 price <= 0'
         WHEN stock_code NOT GLOB '[0-9][0-9][0-9][0-9][0-9]*' THEN '3 non-product code'
         WHEN (invoice LIKE 'C%' AND quantity < 0) OR (invoice NOT LIKE 'C%' AND invoice NOT LIKE 'A%' AND quantity > 0) THEN '5 kept'
         ELSE '4 other (adjustments / inconsistent sign)'
       END AS fate,
       COUNT(*) AS raw_rows
FROM raw_transactions GROUP BY 1 ORDER BY 1;
