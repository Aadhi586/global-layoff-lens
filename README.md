# Global Layoff Lens

**Explore Global Workforce Trends Through Data.**

Global Layoff Lens is an educational exploratory data analysis project. It turns a real Kaggle layoffs snapshot into a reproducible Python data pipeline, FastAPI endpoints, and a responsive interactive web experience. Explore records, compare company histories, inspect distributions, and see precisely how missing data affects interpretation.

## Dataset first

- Source: [Layoffs Dataset on Kaggle](https://www.kaggle.com/datasets/swaptr/layoffs-2022) (`swaptr/layoffs-2022`)
- Snapshot acquired: 2026-10-03
- Downloaded snapshot: 4,615 rows, 11 columns; event dates 2020-03-11 to 2026-09-23
- Raw download and extracted CSV are preserved in `data/raw/`; the reproducible output is `data/processed/layoffs_cleaned.csv`.
- The schema, cardinalities, source field types, and source missingness are recorded in [`data/metadata/data_dictionary.md`](data/metadata/data_dictionary.md). Source and snapshot notes are in [`data/metadata/dataset_source.md`](data/metadata/dataset_source.md).

The dataset is a time-varying snapshot. All totals, rankings, and insights describe the downloaded rows and do not represent complete company workforce histories.

## What is included

- Dataset explorer with search, year/country/industry filters, pagination, and source-linked event records.
- Company explorer with event timeline, locations, reported workforce percentages, source links, and a transparent descriptive Historical Stability Indicator.
- Company comparison with matched definitions and side-by-side timelines.
- Industry, country, and time-series analyses with filters.
- EDA Lab with descriptive statistics, numeric histograms, IQR-based outlier counts in the pipeline report, and a Pearson correlation matrix.
- Data Cleaning view generated from the processing report, including before/after schema and missing-value profile.
- Data-derived observation cards with their calculation basis.
- About page with methodology, data source, and limitations.
- FastAPI endpoints documented at `/docs` while the API is running.

## Architecture

```text
Kaggle snapshot (raw CSV + original ZIP)
  → pandas validation, cleaning, schema and EDA report
  → processed CSV + JSON cleaning/EDA metadata
  → FastAPI (`backend/app.py`)
  → Next.js / React / Recharts (`frontend/`)
```

### Cleaning methodology

The reusable pipeline trims text whitespace, parses the observed `date` and `date_added` fields, checks the three observed numeric fields, counts invalid/negative values, removes exact duplicate rows, and excludes rows only if the required company or event date is missing. Unknown numeric and categorical values are retained as missing. It creates `cleaning_report.json` and `eda_summary.json`; it does not silently impute values or overwrite the raw data.

### EDA methodology

The pipeline calculates numeric summaries (count, mean, standard deviation, quartiles, range, and 1.5×IQR outlier count), category cardinalities/top categories, date coverage, and numeric correlations. API aggregations are calculated from the cleaned snapshot. For `percentage_laid_off`, stored fractions are displayed as percentages. `funds_raised` follows the source dataset's units; check source documentation before interpreting it outside this project.

The Historical Stability Indicator is an explicitly heuristic descriptive score. It subtracts capped penalties for recorded event frequency, total known layoff volume, and average reported workforce percentage, then adds a capped bonus for time since the last recorded event. The API returns every component and its formula. The weights are design choices, not statistically validated coefficients; this is not a risk forecast, job-security rating, or company-performance measure.

## Run locally

Requirements: Python 3.10+ and Node.js 20+.

### Windows quick start

Double-click [`start.bat`](start.bat) in the project folder. It creates a local Python environment if needed, installs dependencies, prepares the data, starts the API and website, checks that both are responding, and opens the site at `http://127.0.0.1:3000`. Keep the launcher window open while using the site. Double-click `stop.bat` when finished. The first launch needs an internet connection to install dependencies.

If the page says “Failed to fetch,” the API did not start or the launcher was closed. Run `start.bat` again and read its message; startup logs are saved under `.runtime/`.

### Backend

From this project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.services.data_cleaner
uvicorn backend.app:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

To intentionally acquire a fresh upstream snapshot, run `python scripts/download_kaggle_dataset.py`. It writes a timestamped archive and CSV under `data/raw/snapshots/` and leaves the original raw files unchanged. To process that vintage, pass its CSV path to `python -m backend.services.data_cleaner --raw-path data/raw/snapshots/<timestamp>/layoffs_raw.csv`.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. To use a different backend origin, set `NEXT_PUBLIC_API_URL` to the API base path (for example, `http://127.0.0.1:8000/api`) before starting/building the frontend.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Dataset/API readiness |
| `GET /api/overview` | Filtered totals and snapshot date range |
| `GET /api/dataset` | Search, sort, pagination, field selection, filters |
| `GET /api/companies` | Company directory and search |
| `GET /api/company/{name}` | Company profile, events, timeline |
| `GET /api/compare?company_a=…&company_b=…` | Side-by-side comparison |
| `GET /api/industries`, `/api/countries` | Filtered group summaries |
| `GET /api/trends?granularity=month\|year` | Time series |
| `GET /api/eda/statistics` | Descriptive statistics |
| `GET /api/eda/distributions?field=…` | Histogram bins |
| `GET /api/eda/correlation` | Numeric Pearson correlation matrix |
| `GET /api/cleaning` | Pipeline report |
| `GET /api/insights` | Snapshot-derived observations with calculation notes |
| `GET /api/stability?name=…` | Descriptive company indicator with components and caveat |

Supported global filters include `year`, `country`, `industry`, `company`, `stage`, `start_date`, and `end_date` where applicable. Invalid dates, sort parameters, and unknown fields return useful 422 errors; unknown companies return 404.

## Project structure

```text
backend/                 FastAPI app and pandas cleaning pipeline
data/raw/                Original Kaggle ZIP and extracted source CSV
data/processed/          Reproducible cleaned CSV
data/metadata/           Source notes, data dictionary, cleaning/EDA reports
frontend/app/             Next.js interface and responsive styles
```

## Checks

Install `requirements-dev.txt`, then run `python -m unittest discover -s backend/tests -v`. The suite checks the cleaning behavior, API endpoints, filters, pagination, comparison, invalid inputs, and not-found/empty results.

## Limitations

- Layoff records may be incomplete and reporting varies by company and country.
- Historical records do not represent a company's complete employment history.
- Missing counts and percentages affect aggregation and comparison coverage.
- The indicator and insights are descriptive only. They do not predict future layoffs, job security, or company performance.
- The downloadable Kaggle dataset changes over time; refreshes require reacquisition, inspection, and regeneration of the documented pipeline outputs.

## Future work

Possible extensions include additional verified workforce sources, refreshed snapshots, job-posting and hiring trends, and salary/skills analysis. Such additions should use documented real sources and preserve provenance.
