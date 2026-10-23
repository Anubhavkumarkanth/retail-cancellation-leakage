"""Run the whole pipeline: load -> SQL -> analysis -> dashboard/workbook."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = ["scripts/download_data.py", "src/load_data.py", "src/run_sql.py", "src/analysis.py", "src/build_outputs.py"]

for step in STEPS:
    print(f"\n==> {step}")
    subprocess.run([sys.executable, str(ROOT / step)], check=True, cwd=ROOT)
print("\nDone. Open reports/dashboard.html and outputs/cancellation_summary.xlsx; run `pytest -q` to validate.")
