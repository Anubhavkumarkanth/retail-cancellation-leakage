"""Statistics and figures for the cancellation analysis. Reads outputs/csv/*.csv and data/retail.db."""
import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "outputs" / "csv"
FIG = ROOT / "reports" / "figures"
SEED = 20261024
N_BOOT = 2000
INK, MUTED, ACCENT, ALERT = "#1f2937", "#9ca3af", "#2563eb", "#dc2626"


def top_share(values: pd.Series, frac: float) -> float:
    """Share of the total held by the top `frac` of positive values."""
    v = values[values > 0].sort_values(ascending=False)
    k = max(1, round(len(v) * frac))
    return float(v.head(k).sum() / v.sum())


def cluster_bootstrap_rate(df: pd.DataFrame, rng: np.random.Generator) -> tuple[float, float, float]:
    """Customers are the resampling unit because a customer's lines are not independent."""
    spend, canc = df["spend_gbp"].to_numpy(), df["other_cancelled_gbp"].to_numpy()
    n = len(df)
    point = canc.sum() / spend.sum()
    idx = rng.integers(0, n, size=(N_BOOT, n))
    rates = canc[idx].sum(axis=1) / spend[idx].sum(axis=1)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK)


def main() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    kpi = pd.read_csv(CSV / "kpi_overview.csv").iloc[0]
    monthly = pd.read_csv(CSV / "monthly.csv")
    country = pd.read_csv(CSV / "country.csv")
    skus = pd.read_csv(CSV / "sku_top_cancelled.csv")
    freq = pd.read_csv(CSV / "customer_cancel_frequency.csv")
    cust = pd.read_csv(CSV / "customer_level.csv")

    findings: dict = {"kpi": {k: float(v) for k, v in kpi.items()}}

    # --- concentration among customers with a non-reversal cancellation
    canc_customers = cust[cust["other_cancelled_gbp"] > 0]
    findings["customers_with_other_cancellation"] = int(len(canc_customers))
    findings["identified_customers"] = int(len(cust))
    findings["customer_concentration"] = {
        f"top_{int(f * 100)}pct": round(top_share(canc_customers["other_cancelled_gbp"], f) * 100, 1)
        for f in (0.01, 0.05, 0.10)
    }

    # --- overall rate with customer-clustered bootstrap CI (identified customers only)
    p, lo, hi = cluster_bootstrap_rate(cust, rng)
    findings["identified_customer_rate_pct"] = {"point": round(p * 100, 2), "ci95": [round(lo * 100, 2), round(hi * 100, 2)]}

    # --- country rates with CI, plus leave-one-customer-out for the largest canceller in each country
    rows = []
    for c in ("United Kingdom", "France", "Spain", "Germany"):
        sub = cust[cust["country"] == c]
        pt, l, h = cluster_bootstrap_rate(sub, rng)
        top = sub.sort_values("other_cancelled_gbp", ascending=False).iloc[0]
        rest = sub.drop(top.name)
        rows.append({
            "country": c, "customers": int(len(sub)), "rate_pct": round(pt * 100, 2),
            "ci_low_pct": round(l * 100, 2), "ci_high_pct": round(h * 100, 2),
            "top_customer_share_of_cancelled_pct": round(top["other_cancelled_gbp"] / sub["other_cancelled_gbp"].sum() * 100, 1),
            "rate_without_top_customer_pct": round(rest["other_cancelled_gbp"].sum() / rest["spend_gbp"].sum() * 100, 2),
        })
    country_ci = pd.DataFrame(rows)
    country_ci.to_csv(CSV / "country_bootstrap.csv", index=False)
    findings["country_bootstrap"] = rows

    # --- which single customer explains each high-rate month
    con = sqlite3.connect(ROOT / "data" / "retail.db")
    spikes = []
    for m in monthly.loc[monthly["adjusted_rate_pct"] > 3, "invoice_month"]:
        d = pd.read_sql(
            "SELECT customer_id, SUM(line_value) v FROM cancellation_class "
            "WHERE invoice_month = ? AND cancel_class != 'reversal_24h' GROUP BY 1 ORDER BY v DESC", con, params=(m,))
        spikes.append({"month": m, "top_customer_share_pct": round(float(d["v"].iloc[0] / d["v"].sum() * 100), 1),
                       "adjusted_rate_pct": float(monthly.loc[monthly.invoice_month == m, "adjusted_rate_pct"].iloc[0])})
    findings["high_rate_months"] = spikes
    pd.DataFrame(spikes).to_csv(CSV / "high_rate_months.csv", index=False)

    # --- figures
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(monthly["invoice_month"], monthly["headline_rate_pct"], color=MUTED, lw=2, label="Headline rate (all cancelled value)")
    ax.plot(monthly["invoice_month"], monthly["adjusted_rate_pct"], color=ACCENT, lw=2.5, label="Adjusted rate (same-day reversals removed)")
    for m in ("2011-01", "2011-12"):
        r = monthly[monthly.invoice_month == m].iloc[0]
        ax.annotate(f"{r.headline_rate_pct:.1f}%", (m, r.headline_rate_pct), textcoords="offset points", xytext=(-6, 6), color=INK, fontsize=9, ha="right")
    ax.set_ylabel("Cancelled value / gross sales (%)")
    ax.set_xticks(range(0, len(monthly), 3), monthly["invoice_month"][::3], rotation=0, fontsize=8)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    style(ax, "The two biggest spikes are reversed bulk orders, not a returns problem")
    fig.tight_layout(); fig.savefig(FIG / "01_monthly_headline_vs_adjusted.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.2))
    parts = [("Same-day reversals", kpi.reversal_24h_gbp, ALERT), ("Other cancellations", kpi.other_cancelled_gbp, ACCENT), ("No customer ID", kpi.unmatched_gbp, MUTED)]
    left = 0
    for name, v, col in parts:
        ax.barh([0], [v / 1000], left=left, color=col, label=f"{name}: £{v / 1000:,.0f}k")
        left += v / 1000
    ax.set_yticks([]); ax.set_xlabel("Cancelled value (£ thousand)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=1, fontsize=9)
    style(ax, "About half of cancelled value is same-day reversals")
    fig.tight_layout(); fig.savefig(FIG / "02_cancelled_value_split.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    labels = skus["description"].str.title().str.slice(0, 32) + " (" + skus["rate_pct"].round(0).astype(int).astype(str) + "%)"
    ax.barh(labels[::-1], skus["other_cancelled_gbp"][::-1] / 1000, color=ACCENT)
    ax.set_xlabel("Non-reversal cancelled value (£ thousand); label = share of that SKU's sales")
    style(ax, "Top 15 SKUs by cancelled value")
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout(); fig.savefig(FIG / "03_top_skus.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4))
    err = [country_ci["rate_pct"] - country_ci["ci_low_pct"], country_ci["ci_high_pct"] - country_ci["rate_pct"]]
    ax.bar(country_ci["country"], country_ci["rate_pct"], yerr=err, color=ACCENT, capsize=4, label="Rate with 95% bootstrap CI")
    ax.scatter(country_ci["country"], country_ci["rate_without_top_customer_pct"], color=ALERT, zorder=3, label="Rate without the largest canceller")
    ax.set_ylabel("Non-reversal cancelled value / spend (%), identified customers")
    ax.legend(frameon=False, fontsize=9)
    style(ax, "Spain's high rate is one customer, and its CI is very wide")
    fig.tight_layout(); fig.savefig(FIG / "04_country_rates_ci.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(freq["cancel_invoice_band"], freq["rate_pct"], color=ACCENT)
    for i, r in freq.iterrows():
        ax.text(i, r.rate_pct + 0.05, f"{int(r.customers):,} customers\n£{r.spend_gbp / 1e6:.1f}m spend", ha="center", fontsize=8, color=INK)
    ax.set_xlabel("Cancellation invoices per customer"); ax.set_ylabel("Cancelled value / spend (%)")
    ax.set_ylim(0, freq["rate_pct"].max() * 1.5)
    style(ax, "Customers who cancel: about 2.7% of spend, at any frequency")
    fig.tight_layout(); fig.savefig(FIG / "05_cancel_frequency_bands.png", dpi=160); plt.close(fig)

    (ROOT / "outputs" / "findings.json").write_text(json.dumps(findings, indent=2))
    return findings


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
