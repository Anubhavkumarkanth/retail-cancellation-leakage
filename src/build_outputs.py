"""Build the HTML dashboard and the Excel summary workbook from outputs/csv/*.csv."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "outputs" / "csv"
BLUE, GREY, RED = "#2563eb", "#9ca3af", "#dc2626"


def dashboard() -> Path:
    kpi = pd.read_csv(CSV / "kpi_overview.csv").iloc[0]
    monthly = pd.read_csv(CSV / "monthly.csv")
    skus = pd.read_csv(CSV / "sku_top_cancelled.csv")
    ctry = pd.read_csv(CSV / "country_bootstrap.csv")

    fig = make_subplots(
        rows=2, cols=2, vertical_spacing=0.22, horizontal_spacing=0.12,
        subplot_titles=("Monthly cancellation rate, with and without reversals", "Where the cancelled value comes from (£)",
                        "Top 10 products by cancelled value, excluding reversals (£)", "Rate by country, with 95% confidence ranges"),
    )
    fig.add_trace(go.Scatter(x=monthly.invoice_month, y=monthly.headline_rate_pct, name="All cancellations", line=dict(color=GREY, width=2)), 1, 1)
    fig.add_trace(go.Scatter(x=monthly.invoice_month, y=monthly.adjusted_rate_pct, name="Without reversals", line=dict(color=BLUE, width=3)), 1, 1)
    fig.add_trace(go.Bar(x=["Reversed within 24 hours", "Other cancellations", "No customer ID"],
                         y=[kpi.reversal_24h_gbp, kpi.other_cancelled_gbp, kpi.unmatched_gbp],
                         marker_color=[RED, BLUE, GREY], showlegend=False), 1, 2)
    top = skus.head(10).iloc[::-1]
    fig.add_trace(go.Bar(y=top.description.str.title().str.slice(0, 30), x=top.other_cancelled_gbp, orientation="h",
                         marker_color=BLUE, customdata=top.rate_pct, hovertemplate="%{y}<br>£%{x:,.0f} (%{customdata}% of the product's sales)<extra></extra>",
                         showlegend=False), 2, 1)
    fig.add_trace(go.Bar(x=ctry.country, y=ctry.rate_pct, marker_color=BLUE, showlegend=False,
                         error_y=dict(type="data", symmetric=False, array=ctry.ci_high_pct - ctry.rate_pct, arrayminus=ctry.rate_pct - ctry.ci_low_pct)), 2, 2)
    fig.add_trace(go.Scatter(x=ctry.country, y=ctry.rate_without_top_customer_pct, mode="markers", name="Without its top cancelling customer",
                             marker=dict(color=RED, size=10)), 2, 2)
    fig.update_yaxes(title_text="% of sales", row=1, col=1)
    fig.update_yaxes(title_text="% of spend (customers with an ID)", row=2, col=2)
    fig.update_layout(height=820, template="simple_white", margin=dict(t=70, l=60, r=30, b=40),
                      legend=dict(orientation="h", y=-0.08), font=dict(family="Segoe UI, Arial", size=12))
    cards = [
        (f"£{kpi.gross_sales_gbp / 1e6:.1f}m", "Product sales, Dec 2009 to Dec 2011"),
        (f"{kpi.headline_rate_pct:.2f}%", "Overall cancellation rate (by value)"),
        (f"{kpi.reversal_share_of_cancelled_pct:.0f}%", "Of the cancelled value is orders reversed within 24 hours"),
        (f"{kpi.adjusted_rate_pct:.2f}%", "Cancellation rate once reversals are left out"),
    ]
    card_html = "".join(f'<div class="card"><b>{v}</b><span>{t}</span></div>' for v, t in cards)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail cancellation leakage dashboard</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px auto;max-width:1100px;color:#1f2937;padding:0 16px}}
h1{{font-size:22px;margin:0 0 4px}}p.sub{{margin:0 0 16px;color:#6b7280}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:8px}}
.card{{border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px}}.card b{{display:block;font-size:26px}}.card span{{font-size:12px;color:#6b7280}}
.note{{font-size:12px;color:#6b7280}}</style></head><body>
<h1>Retail cancellation leakage</h1>
<p class="sub">Real sales from one UK online gift retailer (UCI Online Retail II), Dec 2009 to Dec 2011. Products only; the README lists the cleaning rules.</p>
<div class="cards">{card_html}</div>
{fig.to_html(full_html=False, include_plotlyjs="cdn")}
<p class="note">Rate without reversals = cancellations other than reversals ÷ (sales minus the reversed sales). A reversal is when the same customer cancels the same product and quantity within 24 hours of buying it.
The data gives no reasons for cancelling, so cancellations include returns, order-entry corrections and cancelled orders.</p>
</body></html>"""
    out = ROOT / "reports" / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def workbook() -> Path:
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="E5E7EB")

    def sheet(name: str, df: pd.DataFrame, rate_formula: tuple[str, str, str] | None = None):
        ws = wb.create_sheet(name)
        ws.append(list(df.columns))
        for row in df.itertuples(index=False):
            ws.append(list(row))
        for c in ws[1]:
            c.font, c.fill = Font(bold=True), head_fill
        if rate_formula:  # (new column title, numerator column letter, denominator column letter)
            title, num, den = rate_formula
            col = ws.max_column + 1
            ws.cell(row=1, column=col, value=title).font = Font(bold=True)
            for r in range(2, ws.max_row + 1):
                ws.cell(row=r, column=col, value=f"=ROUND(100*{num}{r}/{den}{r},2)")
        for i, col in enumerate(ws.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = max(12, min(40, max(len(str(c.value or "")) for c in col) + 2))
        ws.freeze_panes = "A2"

    wb.remove(wb.active)
    readme = wb.create_sheet("README")
    for line in [
        "Retail cancellation leakage - summary tables",
        "Source: UCI Online Retail II (CC BY 4.0). Built by src/build_outputs.py from outputs/csv/*.csv.",
        "Values are GBP. 'other' cancellations exclude same-day reversals (same customer, SKU and quantity within 24h of the sale).",
        "Columns headed '(formula)' are live Excel formulas that recompute a rate from the neighbouring columns.",
    ]:
        readme.append([line])
    readme.column_dimensions["A"].width = 120
    readme["A1"].font = Font(bold=True, size=13)
    sheet("KPIs", pd.read_csv(CSV / "kpi_overview.csv").T.reset_index().rename(columns={"index": "metric", 0: "value"}))
    sheet("Monthly", pd.read_csv(CSV / "monthly.csv"), ("other_pct_of_gross (formula)", "D", "B"))
    sheet("Country", pd.read_csv(CSV / "country.csv"))
    sheet("Top SKUs", pd.read_csv(CSV / "sku_top_cancelled.csv"), ("rate_pct (formula)", "C", "D"))
    sheet("Customer bands", pd.read_csv(CSV / "customer_cancel_frequency.csv"), ("rate_pct (formula)", "D", "C"))
    sheet("Data quality", pd.read_csv(CSV / "data_quality_fates.csv"))
    out = ROOT / "outputs" / "cancellation_summary.xlsx"
    wb.save(out)
    return out


if __name__ == "__main__":
    print(dashboard())
    print(workbook())
