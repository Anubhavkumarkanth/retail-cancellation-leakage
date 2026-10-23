"""Capture reports/dashboard_screenshot.png from the generated dashboard (needs: playwright install chromium)."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1180, "height": 1000})
    page.goto((ROOT / "reports" / "dashboard.html").as_uri())
    page.wait_for_selector(".js-plotly-plot .main-svg", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(ROOT / "reports" / "dashboard_screenshot.png"), full_page=True)
    browser.close()
print("saved reports/dashboard_screenshot.png")
