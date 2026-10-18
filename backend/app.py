"""Global Layoff Lens API. Every result is computed from the cleaned Kaggle snapshot."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import math

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "layoffs_cleaned.csv"
app = FastAPI(title="Global Layoff Lens API", version="1.0.0", description="EDA API over the documented Kaggle layoffs snapshot.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])


def data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise HTTPException(503, "Processed dataset is missing. Run `python -m backend.services.data_cleaner` first.")
    frame = pd.read_csv(DATA_PATH, parse_dates=["date", "date_added"])
    if "year" not in frame:
        frame["year"] = frame.date.dt.year
    return frame


def filtered(year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None,
             company: Optional[str] = None, stage: Optional[str] = None,
             start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    df = data()
    if year is not None: df = df[df.date.dt.year == year]
    for column, value in (("country", country), ("industry", industry), ("company", company), ("stage", stage)):
        if value: df = df[df[column].str.casefold() == value.strip().casefold()]
    if start_date:
        try: df = df[df.date >= pd.Timestamp(start_date)]
        except Exception: raise HTTPException(422, "start_date must be an ISO date (YYYY-MM-DD).")
    if end_date:
        try: df = df[df.date <= pd.Timestamp(end_date)]
        except Exception: raise HTTPException(422, "end_date must be an ISO date (YYYY-MM-DD).")
    if start_date and end_date and start_date > end_date: raise HTTPException(422, "start_date must not be after end_date.")
    return df


def records(df: pd.DataFrame) -> list[dict]:
    clean = df.astype(object).where(pd.notna(df), None)
    for col in ("date", "date_added"):
        if col in clean: clean[col] = clean[col].map(lambda x: x.strftime("%Y-%m-%d") if x is not None else None)
    return clean.to_dict(orient="records")


def totals(df: pd.DataFrame) -> dict:
    return {"events": int(len(df)), "layoffs": numeric_sum(df.total_laid_off),
            "countries": int(df.country.nunique()), "companies": int(df.company.nunique()),
            "industries": int(df.industry.nunique()), "events_with_layoff_counts": int(df.total_laid_off.notna().sum())}


def numeric_sum(series: pd.Series) -> Optional[int]:
    value = series.sum(min_count=1)
    return int(value) if pd.notna(value) else None


@app.get("/api/health")
def health(): return {"status": "ok", "dataset_ready": DATA_PATH.exists()}


@app.get("/api/overview")
def overview(year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None,
             stage: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    df = filtered(year, country, industry, stage=stage, start_date=start_date, end_date=end_date)
    return {**totals(df), "date_range": {"start": df.date.min().strftime("%Y-%m-%d") if len(df) else None,
             "end": df.date.max().strftime("%Y-%m-%d") if len(df) else None},
            "stage_options": sorted(data().stage.dropna().astype(str).unique().tolist()),
            "data_note": "Counts reflect records in this snapshot; unknown layoff counts are excluded from the total."}


@app.get("/api/dataset")
def dataset(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
            search: Optional[str] = None, sort_by: str = "date", sort_order: str = "desc",
            year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None,
            company: Optional[str] = None, stage: Optional[str] = None, start_date: Optional[str] = None,
            end_date: Optional[str] = None, columns: Optional[str] = None):
    df = filtered(year, country, industry, company, stage, start_date, end_date)
    if search:
        mask = pd.Series(False, index=df.index)
        for col in ["company", "industry", "country", "location"]:
            mask |= df[col].fillna("").str.contains(search, case=False, regex=False)
        df = df[mask]
    if sort_by not in df.columns: raise HTTPException(422, f"sort_by must be one of: {', '.join(df.columns)}")
    if sort_order not in ("asc", "desc"): raise HTTPException(422, "sort_order must be asc or desc")
    df = df.sort_values(sort_by, ascending=sort_order == "asc", na_position="last", kind="stable")
    count = len(df)
    selected = [c.strip() for c in columns.split(",") if c.strip()] if columns else list(df.columns.drop("year", errors="ignore"))
    unknown = set(selected) - set(df.columns)
    if unknown: raise HTTPException(422, f"Unknown columns: {', '.join(sorted(unknown))}")
    page_df = df.iloc[(page-1)*page_size:page*page_size][selected]
    return {"rows": records(page_df), "total": count, "page": page, "page_size": page_size,
            "pages": math.ceil(count/page_size), "columns": selected}


@app.get("/api/companies")
def companies(search: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    df = data()
    grouped = df.groupby("company", dropna=True).agg(events=("company", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1)),
            countries=("country", "nunique"), industry=("industry", "first"), country=("country", "first"), last_event=("date", "max")).reset_index()
    if search: grouped = grouped[grouped.company.str.contains(search, case=False, regex=False)]
    grouped = grouped.sort_values(["layoffs", "events"], ascending=False).head(limit)
    return {"items": records(grouped), "total_matches": int(len(grouped))}


@app.get("/api/search")
def global_search(q: str = Query(..., min_length=1, max_length=100), limit: int = Query(8, ge=1, le=20)):
    df = data(); term = q.strip()
    if not term: return {"companies": [], "industries": [], "countries": []}
    company_matches = df[df.company.str.contains(term, case=False, regex=False)].groupby("company").agg(
        events=("company", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1)),
        industry=("industry", "first"), country=("country", "first")).reset_index().sort_values("layoffs", ascending=False, na_position="last").head(limit)
    industries_matches = sorted([str(v) for v in df.industry.dropna().unique() if term.casefold() in str(v).casefold()])[:limit]
    country_matches = sorted([str(v) for v in df.country.dropna().unique() if term.casefold() in str(v).casefold()])[:limit]
    return {"companies": records(company_matches), "industries": industries_matches, "countries": country_matches}


@app.get("/api/company/{name}")
def company(name: str):
    df = data(); subset = df[df.company.str.casefold() == name.casefold()]
    if subset.empty: raise HTTPException(404, "No matching company in this dataset snapshot.")
    timeline = subset.assign(period=subset.date.dt.to_period("M").astype(str)).groupby("period").agg(events=("company", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1))).reset_index()
    return {"company": subset.company.iloc[0], "industry": subset.industry.mode().iloc[0] if subset.industry.notna().any() else None,
            "countries": sorted(subset.country.dropna().unique().tolist()), "events": int(len(subset)),
            "layoffs": numeric_sum(subset.total_laid_off), "largest_event": None if subset.total_laid_off.isna().all() else int(subset.total_laid_off.max()),
            "timeline": records(timeline), "records": records(subset.sort_values("date", ascending=False)),
            "note": "Figures represent records available in the dataset and may not represent the company's complete workforce history."}


@app.get("/api/compare")
def compare(company_a: str, company_b: str):
    if company_a.casefold() == company_b.casefold(): raise HTTPException(422, "Choose two different companies.")
    result = []
    for name in (company_a, company_b):
        subset = data(); subset = subset[subset.company.str.casefold() == name.casefold()]
        if subset.empty: raise HTTPException(404, f"No matching company: {name}")
        result.append({"company": subset.company.iloc[0], "industry": subset.industry.mode().iloc[0] if subset.industry.notna().any() else None,
            "countries": sorted(subset.country.dropna().unique().tolist()), "events": int(len(subset)),
            "layoffs": numeric_sum(subset.total_laid_off), "largest_event": None if subset.total_laid_off.isna().all() else int(subset.total_laid_off.max()),
            "percentage_reported": int(subset.percentage_laid_off.notna().sum()),
            "timeline": records(subset.assign(period=subset.date.dt.to_period("M").astype(str)).groupby("period").agg(events=("company", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1))).reset_index())})
    return {"companies": result, "note": "Historical records in this snapshot; comparisons may be affected by missing or uneven reporting."}


@app.get("/api/industries")
def industries(year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None, stage: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    df = filtered(year=year, country=country, industry=industry, stage=stage, start_date=start_date, end_date=end_date)
    g = df.groupby("industry", dropna=False).agg(events=("industry", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1)), companies=("company", "nunique")).reset_index().sort_values("layoffs", ascending=False, na_position="last")
    return {"items": records(g)}


@app.get("/api/countries")
def countries(year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None, stage: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    df = filtered(year=year, country=country, industry=industry, stage=stage, start_date=start_date, end_date=end_date)
    g = df.groupby("country", dropna=False).agg(events=("country", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1)), companies=("company", "nunique")).reset_index().sort_values("layoffs", ascending=False, na_position="last")
    return {"items": records(g)}


@app.get("/api/stages")
def stages():
    df = data()
    return {"items": [{"stage": str(value), "events": int(count)} for value, count in df.stage.value_counts(dropna=True).items()]}


@app.get("/api/trends")
def trends(granularity: str = "month", year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None, stage: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    if granularity not in ("month", "year"): raise HTTPException(422, "granularity must be month or year")
    df = filtered(year=year, country=country, industry=industry, stage=stage, start_date=start_date, end_date=end_date)
    df = df.assign(period=df.date.dt.to_period("M" if granularity == "month" else "Y").astype(str))
    g = df.groupby("period").agg(events=("company", "size"), layoffs=("total_laid_off", lambda s: s.sum(min_count=1)), companies=("company", "nunique")).reset_index()
    return {"granularity": granularity, "items": records(g)}


@app.get("/api/eda/statistics")
def statistics(year: Optional[int] = None, country: Optional[str] = None, industry: Optional[str] = None, stage: Optional[str] = None):
    df = filtered(year, country, industry, stage=stage)
    out = {}
    for col in ("total_laid_off", "percentage_laid_off", "funds_raised"):
        s = df[col].dropna(); q1 = None if s.empty else float(s.quantile(.25)); q3 = None if s.empty else float(s.quantile(.75))
        out[col] = {"count": int(s.count()), "mean": None if s.empty else float(s.mean()), "median": None if s.empty else float(s.median()), "std": None if len(s)<2 else float(s.std()), "min": None if s.empty else float(s.min()), "q1": q1, "q3": q3, "max": None if s.empty else float(s.max()),
                    "outlier_count_iqr": 0 if s.empty else int(((s < q1 - 1.5 * (q3-q1)) | (s > q3 + 1.5 * (q3-q1))).sum())}
    return {"events": int(len(df)), "unique_companies": int(df.company.nunique()), "unique_countries": int(df.country.nunique()), "numeric": out}


@app.get("/api/eda/distributions")
def distributions(field: str = "total_laid_off", bins: int = Query(20, ge=5, le=60)):
    if field not in ("total_laid_off", "percentage_laid_off", "funds_raised"): raise HTTPException(422, "Unsupported numeric field.")
    s = data()[field].dropna()
    if s.empty: return {"field": field, "items": []}
    counts, edges = __import__("numpy").histogram(s, bins=bins)
    return {"field": field, "items": [{"from": float(edges[i]), "to": float(edges[i+1]), "count": int(counts[i])} for i in range(len(counts))]}


@app.get("/api/eda/correlation")
def correlation():
    cols = ["total_laid_off", "percentage_laid_off", "funds_raised"]
    corr = data()[cols].corr(min_periods=2)
    return {"fields": cols, "matrix": [[None if pd.isna(v) else round(float(v), 4) for v in row] for row in corr.values.tolist()]}


@app.get("/api/cleaning")
def cleaning():
    path = ROOT / "data" / "metadata" / "cleaning_report.json"
    if not path.exists(): raise HTTPException(503, "Cleaning report is missing; run the cleaning pipeline first.")
    import json
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/insights")
def insights():
    df = data(); totals_by_year = df.assign(year=df.date.dt.year).groupby("year").total_laid_off.sum().dropna()
    largest = df.nlargest(1, "total_laid_off").iloc[0]
    country = df.groupby("country").total_laid_off.sum().idxmax()
    industry = df.groupby("industry").total_laid_off.sum().idxmax()
    latest_year = int(totals_by_year.index.max()); latest_total = int(totals_by_year.loc[latest_year])
    return {"items": [
        {"title": "Largest recorded event", "detail": f"{largest.company} has the largest single event in this snapshot: {int(largest.total_laid_off):,} reported layoffs on {largest.date:%b %d, %Y}.", "basis": "Maximum non-missing total_laid_off record."},
        {"title": "Highest recorded country total", "detail": f"{country} has the largest sum of reported layoff counts in this snapshot.", "basis": "Sum of non-missing total_laid_off, grouped by country."},
        {"title": "Highest recorded industry total", "detail": f"{industry} has the largest sum of reported layoff counts in this snapshot.", "basis": "Sum of non-missing total_laid_off, grouped by industry."},
        {"title": f"{latest_year} recorded total", "detail": f"{latest_total:,} layoffs are recorded in {latest_year} in this snapshot.", "basis": f"Sum of non-missing total_laid_off for event dates in {latest_year}."}
    ], "caveat": "Insights describe recorded data only and may change with coverage and missing values."}


@app.get("/api/stability")
def stability(name: str):
    subset = data(); subset = subset[subset.company.str.casefold() == name.casefold()]
    if subset.empty: raise HTTPException(404, "No matching company in this dataset snapshot.")
    events = len(subset); known_counts = int(subset.total_laid_off.notna().sum()); total = numeric_sum(subset.total_laid_off)
    average_percentage = None if subset.percentage_laid_off.dropna().empty else float(subset.percentage_laid_off.mean())
    recency_days = max(0, int((pd.Timestamp.now().normalize() - subset.date.max()).days))
    event_penalty = min(events * 10, 30)
    volume_penalty = 0 if total is None else min(total / 5000 * 20, 25)
    percentage_penalty = 0 if average_percentage is None else average_percentage * 25
    recency_bonus = min(recency_days / 3650 * 20, 20)
    score = round(max(0, min(100, 100 - event_penalty - volume_penalty - percentage_penalty + recency_bonus)))
    return {"company": subset.company.iloc[0], "indicator": score,
            "components": {"recorded_events": events, "events_with_layoff_counts": known_counts, "total_recorded_layoffs": total,
                           "average_reported_workforce_percentage": average_percentage, "days_since_last_record": recency_days,
                           "event_frequency_penalty": event_penalty, "layoff_volume_penalty": round(volume_penalty, 2),
                           "percentage_penalty": round(percentage_penalty, 2), "recency_bonus": round(recency_bonus, 2)},
            "formula": "100 − min(events × 10, 30) − min(total_layoffs ÷ 5,000 × 20, 25) − (average_reported_percentage × 25) + min(days_since_last_record ÷ 3,650 × 20, 20), bounded to 0–100.",
            "note": "This heuristic summarizes historical patterns present in this dataset snapshot. Its weights are descriptive design choices; it does not predict future layoffs, job security, or company performance."}
