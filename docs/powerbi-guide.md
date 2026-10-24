# Power BI report guide

You build this report yourself in Power BI Desktop (free, Windows). The CSVs come from
`scripts/export_star_schema.py`; a draft run on 24 Oct 2026 produced:

| File | Rows | What it is |
|---|---:|---|
| `fact_lines.csv` | 1,032,918 | One row per clean product line (sale or cancellation) |
| `dim_date.csv` | 739 | One row per day, 2009-12-01 to 2011-12-09 |
| `dim_product.csv` | 4,892 | One row per stock code |
| `dim_customer.csv` | 5,875 | One row per customer ID (includes customers who only cancelled) |

## 1. Load

Home → Get data → Text/CSV → load each file. In Power Query check the types:
`date_key` whole number, `date` date, `customer_id` whole number, `line_value` and `unit_price` decimal,
`quantity` whole number. Blank `customer_id` (no customer recorded) and blank `cancel_class` (sales) are expected.

## 2. Model (Model view)

| From (one) | To (many) | Notes |
|---|---|---|
| `dim_date[date_key]` | `fact_lines[date_key]` | Mark `dim_date` as date table using `dim_date[date]` |
| `dim_product[stock_code]` | `fact_lines[stock_code]` | |
| `dim_customer[customer_id]` | `fact_lines[customer_id]` | Blank IDs simply don't join |

Single-direction filters, dimension to fact. Use `fact_lines[country]` for country slicers (it is the country on each line);
`dim_customer[country]` is one country per customer.

## 3. Measures (new measure on `fact_lines`)

```DAX
Gross Sales   = CALCULATE ( SUM ( fact_lines[line_value] ), fact_lines[line_type] = "sale" )
Cancelled     = CALCULATE ( SUM ( fact_lines[line_value] ), fact_lines[line_type] = "cancellation" )
Reversals     = CALCULATE ( [Cancelled], fact_lines[cancel_class] = "reversal_24h" )
Headline Rate = DIVIDE ( [Cancelled], [Gross Sales] )
Adjusted Rate = DIVIDE ( [Cancelled] - [Reversals], [Gross Sales] - [Reversals] )
Reversal Share = DIVIDE ( [Reversals], [Cancelled] )
```

Format the three rates as percentages with two decimals. The draft test
`tests/test_star_schema.py::test_dax_measures_reproduce_published_kpis` runs the same arithmetic in pandas and gets
3.65%, 1.88% and 49.5%, so your cards must show exactly those values with no filters applied.

## 4. Report pages

1. **Overview:** cards for Gross Sales (£19,699,785), Cancelled (£719,656), Headline Rate (3.65%), Reversal Share (49.5%),
   Adjusted Rate (1.88%).
2. **Monthly:** line chart, axis `dim_date[year_month]`, values Headline Rate and Adjusted Rate. Dec 2011 and Jan 2011
   should spike on the headline line only.
3. **Products:** table of `dim_product[description]`, Cancelled, Gross Sales; a bar chart of the top 15 by Cancelled with
   `cancel_class` filtered to `other`.
4. **Countries:** bar chart of Adjusted Rate by `fact_lines[country]` with a slicer; note that Spain and France rest on one
   customer each (see README finding 5).

## 5. Verify and export

- With no filters: the five overview numbers above match exactly.
- File → Export → PDF; save page screenshots as PNG.
- Save `retail-cancellation-leakage.pbix`. Commit it only if it is under 50 MB; otherwise attach it to a GitHub release.

## Interview notes

- **Why a star schema?** One fact table, small dimensions; filters flow from dimensions to facts, measures stay short.
- **What does CALCULATE do?** Evaluates an expression under a modified filter context, here restricting to sale or
  cancellation lines.
- **Why DIVIDE instead of `/`?** It returns blank instead of an error when the denominator is zero, for example a month with no sales.
