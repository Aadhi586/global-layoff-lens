"""Reproducible cleaning and profiling for the Kaggle layoffs dataset."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import date

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "layoffs_raw.csv"
PROCESSED = ROOT / "data" / "processed" / "layoffs_cleaned.csv"
METADATA = ROOT / "data" / "metadata"
NUMERIC = ["total_laid_off", "percentage_laid_off", "funds_raised"]
DATE_COLUMNS = ["date", "date_added"]


def inspect(frame: pd.DataFrame) -> dict:
    return {
        "rows": int(len(frame)), "columns": int(frame.shape[1]),
        "missing_by_column": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "duplicate_rows": int(frame.duplicated().sum()),
        "dtypes": {str(k): str(v) for k, v in frame.dtypes.items()},
    }


def clean(raw_path: Path = RAW, processed_path: Path = PROCESSED, metadata_path: Path = METADATA) -> dict:
    source = pd.read_csv(raw_path)
    before = inspect(source)
    df = source.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Trim string fields without changing the underlying records' meaning.
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        df[col] = df[col].replace("", pd.NA)

    invalid = {"date": 0, "date_added": 0, "negative_numeric": 0}
    for col in DATE_COLUMNS:
        if col in df:
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            invalid[col] = int((df[col].notna() & parsed.isna()).sum())
            df[col] = parsed
    for col in NUMERIC:
        if col in df:
            converted = pd.to_numeric(df[col], errors="coerce")
            invalid[f"{col}_non_numeric"] = int((df[col].notna() & converted.isna()).sum())
            invalid[f"{col}_negative"] = int((converted < 0).sum())
            df[col] = converted.mask(converted < 0)
            invalid["negative_numeric"] += invalid[f"{col}_negative"]
    if "percentage_laid_off" in df:
        invalid["percentage_laid_off_above_one"] = int((df["percentage_laid_off"] > 1).sum())
        df["percentage_laid_off"] = df["percentage_laid_off"].mask(df["percentage_laid_off"] > 1)

    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    # Rows with no company or event date cannot identify a usable event.
    required = [c for c in ("company", "date") if c in df]
    invalid_required = int(df[required].isna().any(axis=1).sum()) if required else 0
    if required:
        df = df.dropna(subset=required)
    for col in ("company", "industry", "country", "location", "stage"):
        if col in df:
            df[col] = df[col].astype("string").str.strip()
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_path, index=False, date_format="%Y-%m-%d")
    after = inspect(df)

    numeric_summary = {}
    for col in [c for c in NUMERIC if c in df]:
        s = df[col].dropna()
        numeric_summary[col] = {
            "count": int(s.count()), "mean": None if s.empty else float(s.mean()),
            "std": None if s.empty else float(s.std()),
            "min": None if s.empty else float(s.min()),
            "median": None if s.empty else float(s.median()),
            "q1": None if s.empty else float(s.quantile(.25)),
            "q3": None if s.empty else float(s.quantile(.75)),
            "max": None if s.empty else float(s.max()),
            "outlier_count_iqr": int(((s < s.quantile(.25) - 1.5 * (s.quantile(.75)-s.quantile(.25))) | (s > s.quantile(.75) + 1.5 * (s.quantile(.75)-s.quantile(.25)))).sum()) if not s.empty else 0,
        }
    corr = df[[c for c in NUMERIC if c in df]].corr(min_periods=2).round(4).where(lambda x: x.notna(), None).to_dict()
    eda = {
        "numeric": numeric_summary,
        "correlation": corr,
        "date_range": {"start": df["date"].min().strftime("%Y-%m-%d"), "end": df["date"].max().strftime("%Y-%m-%d")} if "date" in df and len(df) else None,
        "categories": {c: {"unique": int(df[c].nunique(dropna=True)), "top": df[c].value_counts(dropna=True).head(15).to_dict()} for c in ["company", "industry", "country", "stage"] if c in df},
    }
    metadata_path.mkdir(parents=True, exist_ok=True)
    report = {"generated_on": date.today().isoformat(), "source": "Kaggle: swaptr/layoffs-2022", "date_range": eda["date_range"], "before": before,
              "after": after, "removed_duplicates": duplicate_count, "removed_missing_required": invalid_required,
              "invalid_values": invalid, "numeric_summary": numeric_summary}
    (metadata_path / "cleaning_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (metadata_path / "eda_summary.json").write_text(json.dumps(eda, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate, clean, and profile the current layoffs dataset.")
    parser.add_argument("--raw-path", type=Path, default=RAW, help="Raw CSV to process; defaults to data/raw/layoffs_raw.csv")
    parser.add_argument("--processed-path", type=Path, default=PROCESSED)
    parser.add_argument("--metadata-path", type=Path, default=METADATA)
    args = parser.parse_args()
    print(json.dumps(clean(args.raw_path, args.processed_path, args.metadata_path), indent=2, default=str))
