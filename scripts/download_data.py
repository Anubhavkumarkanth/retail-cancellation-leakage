"""Download and unpack UCI Online Retail II (CC BY 4.0) into data/raw/."""
import hashlib
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
# SHA-256 of the zip as downloaded on 2026-10-24; a mismatch means the source changed.
SHA256 = "572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "online_retail_ii.zip"
    if not target.exists():
        urllib.request.urlretrieve(URL, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"Checksum mismatch: {digest}\nThe dataset may have changed; see README 'Data'.")
    zipfile.ZipFile(target).extractall(RAW)
    print("Ready:", RAW / "online_retail_II.xlsx")


if __name__ == "__main__":
    main()
