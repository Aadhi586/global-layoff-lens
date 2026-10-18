# Global Layoff Lens

Explore a documented snapshot of reported workforce reductions through an interactive Next.js dashboard, a FastAPI service, and a reproducible pandas data pipeline.

> **Project type:** Educational exploratory data analysis (EDA) project. The records are a dated snapshot, not a complete census of layoffs or company workforces.

## Contents

- [Features](#features)
- [Data](#data)
- [Technology](#technology)
- [Quick start](#quick-start)
- [Run services separately](#run-services-separately)
- [API](#api)
- [Data preparation and analysis](#data-preparation-and-analysis)
- [Project layout](#project-layout)
- [Tests](#tests)
- [Interpretation and limitations](#interpretation-and-limitations)
- [License](#license)

## Features

- Search and filter layoff event records by company, year, country, industry, and stage.
- Inspect company event histories and compare two companies side by side.
- Explore country, industry, and time trends.
- Review descriptive statistics, distributions, and numeric correlations in the EDA Lab.
- Inspect the cleaning report, missing-value profile, and data dictionary.
- Explore snapshot-derived observations with their calculation basis.
- Use the documented FastAPI endpoints for dataset records and aggregations.

## Data

The project includes a downloaded snapshot of the [Layoffs Dataset on Kaggle](https://www.kaggle.com/datasets/swaptr/layoffs-2022) (`swaptr/layoffs-2022`). The archived snapshot was acquired on **October 3, 2026** and contains **4,615 rows and 11 columns**, with event dates from **March 11, 2020 through September 23, 2026**.

- Original downloaded archive and extracted input: `data/raw/`
- Cleaned output: `data/processed/layoffs_cleaned.csv`
- Source notes, data dictionary, and generated reports: `data/metadata/`

The snapshot can differ from the current upstream Kaggle dataset. Its records and all results in this project describe only the included download. Review [`data/metadata/dataset_source.md`](data/metadata/dataset_source.md) and [`data/metadata/data_dictionary.md`](data/metadata/data_dictionary.md) for provenance and field definitions.

## Technology

| Area | Tools |
| --- | --- |
| Interface | Next.js, React, TypeScript, Recharts |
| API | Python, FastAPI, Uvicorn |
| Data pipeline | Python, pandas, NumPy |
| Tests | Python `unittest` |

## Quick start

### Windows

Install **Python 3.10 or newer** and **Node.js 20 or newer**, then double-click `start.bat` in the project folder. The launcher creates the Python environment if needed, installs dependencies, prepares the dataset, starts the API and website, checks their availability, and opens the site at <http://127.0.0.1:3000>.

Keep the launcher window open while using the app. Use `stop.bat` to stop the local services. The first launch needs an internet connection to install Python and Node dependencies.

### Manual setup

From the project root, prepare the backend and data:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.services.data_cleaner
```

Start the API in that terminal:

```powershell
uvicorn backend.app:app --reload
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The API runs at <http://127.0.0.1:8000>; interactive API documentation is at <http://127.0.0.1:8000/docs>.

To use a different API origin, set `NEXT_PUBLIC_API_URL` to the API base path before starting or building the frontend. An example is provided in [`frontend/.env.example`](frontend/.env.example).

## Run services separately

The backend and frontend can also be started independently on macOS or Linux, provided the same Python and Node.js requirements are installed.

Backend, from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.services.data_cleaner
uvicorn backend.app:app --reload
```

Frontend, from another terminal:

```bash
cd frontend
npm install
npm run dev
```

## API

The API provides health, overview, filtered dataset, company, comparison, industry, country, trend, EDA, cleaning, insight, and company stability endpoints. Open `/docs` while the API is running for request schemas and interactive exploration.

Common endpoints include:

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | API and dataset readiness |
| `GET /api/overview` | Filtered totals and snapshot date range |
| `GET /api/dataset` | Search, filters, sorting, field selection, and pagination |
| `GET /api/companies` | Company directory and search |
| `GET /api/company/{name}` | Company profile, reported events, and timeline |
| `GET /api/compare?company_a=…&company_b=…` | Side-by-side company comparison |
| `GET /api/industries` and `GET /api/countries` | Group summaries |
| `GET /api/trends?granularity=month` | Monthly or yearly time series |
| `GET /api/eda/statistics` | Descriptive numeric statistics |
| `GET /api/eda/distributions?field=…` | Histogram bins for a numeric field |
| `GET /api/eda/correlation` | Numeric Pearson correlation matrix |
| `GET /api/cleaning` | Generated cleaning report |
| `GET /api/insights` | Snapshot-derived observations and calculation notes |
| `GET /api/stability?name=…` | Descriptive indicator and its components |

Supported filters include `year`, `country`, `industry`, `company`, `stage`, `start_date`, and `end_date` where applicable. Invalid filter values return validation errors; an unknown company returns `404`.

## Data preparation and analysis

Run the reproducible cleaning and reporting pipeline from the project root:

```bash
python -m backend.services.data_cleaner
```

The pipeline trims text, parses dates, validates observed numeric fields, counts invalid or negative values, removes exact duplicate rows, and excludes rows missing the required company or event date. Other missing values remain missing; the pipeline does not silently impute them or overwrite the raw input. It writes the cleaned CSV and JSON cleaning and EDA reports.

To intentionally download a fresh upstream snapshot, run:

```bash
python scripts/download_kaggle_dataset.py
```

The script stores a timestamped archive and CSV under `data/raw/snapshots/`. To process one of those downloads, pass its CSV path to the pipeline:

```bash
python -m backend.services.data_cleaner --raw-path data/raw/snapshots/<timestamp>/layoffs_raw.csv
```

## Project layout

```text
backend/                 FastAPI application, data pipeline, and tests
data/raw/                Downloaded Kaggle archive and source CSV
data/processed/          Cleaned CSV used by the application
data/metadata/           Source notes, dictionary, cleaning and EDA reports
frontend/app/            Next.js pages and responsive styles
scripts/                 Snapshot download utility
start.bat, start.ps1     Windows launchers
stop.bat, stop.ps1       Windows service shutdown scripts
```

## Tests

Install the development requirements and run the backend suite from the project root:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s backend/tests -v
```

The tests cover data-cleaning behavior and API endpoints, filters, pagination, comparisons, invalid inputs, and empty or unknown results.

## Interpretation and limitations

- Layoff reporting is incomplete and varies by company, country, and source.
- Historical event rows do not represent a company's full employment history or workforce census.
- Missing employee counts and percentages affect comparisons and totals.
- The **Historical Stability Indicator** is a heuristic descriptive score with design-selected weights. It is not a validated model, forecast, job-security rating, or measure of company performance.
- Snapshot-based observations describe the included data only; they should not be treated as current or comprehensive labor-market statistics.

## License

This project is distributed under the MIT License. See [`LICENSE`](LICENSE) for the full text. The included Kaggle dataset remains subject to its source's terms; the project license does not change those terms.
