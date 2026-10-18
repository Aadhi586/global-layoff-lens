"""Download the public swaptr/layoffs-2022 Kaggle dataset snapshot."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import io

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "snapshots"
URL = "https://www.kaggle.com/api/v1/datasets/download/swaptr/layoffs-2022"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    payload = urlopen(URL, timeout=90).read()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = RAW / stamp
    snapshot.mkdir()
    archive = snapshot / "kaggle_layoffs_2022.zip"
    archive.write_bytes(payload)
    with ZipFile(io.BytesIO(payload)) as bundle:
        csv_files = [name for name in bundle.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            raise RuntimeError("Kaggle archive did not contain a CSV file.")
        if len(csv_files) != 1:
            raise RuntimeError(f"Expected one source CSV, found: {csv_files}")
        (snapshot / "layoffs_raw.csv").write_bytes(bundle.read(csv_files[0]))
    print(f"Downloaded Kaggle snapshot to {snapshot}")
    print("The existing raw dataset has not been changed. To process this vintage, pass its CSV path to the cleaning module.")


if __name__ == "__main__":
    main()
