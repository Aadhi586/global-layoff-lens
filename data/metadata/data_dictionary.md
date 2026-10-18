# Data dictionary

Observed directly from the downloaded Kaggle CSV; no fields were assumed. The dataset has 4,615 rows and 11 columns at acquisition (2026-10-03). Dates in this snapshot range from 2020-03-11 to 2026-09-23.

| Field | Source type | Processed type | Missing (raw) | Meaning |
|---|---|---|---:|---|
| `company` | string | string | 0 | Company named in the layoff record. |
| `location` | string | string | 1 | Location attached to the reported event. |
| `total_laid_off` | float | numeric | 1,600 | Number of employees reported laid off; missing values are preserved. |
| `date` | string | date | 0 | Reported event date. |
| `percentage_laid_off` | float | numeric fraction | 1,728 | Reported share of workforce affected (0–1 in this snapshot; display as percent). |
| `industry` | string | string | 2 | Industry label supplied by the dataset. |
| `source` | string | string | 3 | URL for the report/source of the event. |
| `stage` | string | string | 8 | Company funding/business stage. |
| `funds_raised` | float | numeric, USD millions per source convention | 550 | Funding amount as reported by the source dataset. |
| `country` | string | string | 2 | Country label supplied by the dataset. |
| `date_added` | string | date | 0 | Date record was added to the tracker. |

Observed cardinalities: 2,984 companies, 272 locations, 66 countries, 30 industries, and 16 stages. Numeric available counts are 3,015 for `total_laid_off`, 2,887 for `percentage_laid_off`, and 4,065 for `funds_raised`. The original missing values are retained; unknown counts are excluded from the relevant aggregates.
