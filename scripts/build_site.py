"""Build the GitHub Pages site from the pipeline outputs.

Every number on the landing page comes from outputs/csv and outputs/findings.json, so the page cannot drift from
the tested results. Usage: python build_site.py <repo-root> <site-dir>
"""
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from string import Template

import pandas as pd

REPO_URL = "https://github.com/Anubhavkumarkanth/retail-cancellation-leakage"


def build(repo: Path, site: Path) -> Path:
    site.mkdir(parents=True, exist_ok=True)
    kpi = pd.read_csv(repo / "outputs/csv/kpi_overview.csv").iloc[0]
    conc = pd.read_csv(repo / "outputs/csv/sku_concentration.csv").iloc[0]
    findings = json.loads((repo / "outputs/findings.json").read_text())
    ci = findings["identified_customer_rate_pct"]
    spain = next(c for c in findings["country_bootstrap"] if c["country"] == "Spain")
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()

    shutil.copy2(repo / "reports/dashboard.html", site / "dashboard.html")
    shutil.copytree(repo / "reports/figures", site / "figures", dirs_exist_ok=True)
    (site / "downloads/csv").mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / "outputs/cancellation_summary.xlsx", site / "downloads")
    for csv in (repo / "outputs/csv").glob("*.csv"):
        shutil.copy2(csv, site / "downloads/csv")
    # GitHub Pages does not list directories, so give the CSV folder its own index.
    links = "".join(f'<li><a href="{p.name}">{p.name}</a></li>' for p in sorted((site / "downloads/csv").glob("*.csv")))
    (site / "downloads/csv/index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Query results</title><h1>Query results (CSV)</h1><ul>{links}</ul>", encoding="utf-8")

    values = {
        "headline": f"{kpi.headline_rate_pct:.2f}%",
        "adjusted": f"{kpi.adjusted_rate_pct:.2f}%",
        "reversal_share": f"{kpi.reversal_share_of_cancelled_pct:.1f}%",
        "gross": f"£{kpi.gross_sales_gbp / 1e6:.1f}m",
        "cancelled": f"£{kpi.cancelled_gbp:,.0f}",
        "skus": f"{int(conc.skus_with_other_cancellations):,}",
        "top5": f"{conc.top5pct_skus_share_pct:.1f}%",
        "spain_rate": f"{spain['rate_pct']:.1f}%",
        "spain_top_share": f"{spain['top_customer_share_of_cancelled_pct']:.1f}%",
        "spain_without": f"{spain['rate_without_top_customer_pct']:.1f}%",
        "ci_text": f"{ci['point']:.2f}% (95% CI {ci['ci95'][0]:.2f}% to {ci['ci95'][1]:.2f}%)",
        "repo_url": REPO_URL,
        "built": date.today().isoformat(),
        "commit": commit,
    }
    page = Template((Path(__file__).parent / "site_template.html").read_text(encoding="utf-8")).substitute(values)
    (site / "index.html").write_text(page, encoding="utf-8")
    return site / "index.html"


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), Path(sys.argv[2])))
