# Homework 4 Metrics

## Student Configuration

| Setting | Value |
|---|---|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| Database | s7801_rel |
| Domain | Clinical Trial Listings |

## Technology Configuration

| Component | Value |
|---|---|
| Frontend | React with Vite |
| Backend | FastAPI |
| Database | MySQL 8.4 |
| ORM | SQLAlchemy |
| Local model | qwen3:4b |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Python | 3.11 |

# Database Metrics

## Record Counts

| Table | Record count |
|---|---:|
| clinical_trials | 5,000 |
| trial_sites | 200 |
| users | At least 1 |
| sessions | Depends on current login state |

The `trial_sites.clinical_trial_id` column references `clinical_trials.id`.

# N+1 Performance Experiment

## Experiment Configuration

| Setting | Value |
|---|---:|
| Implementations | 2 |
| Page sizes | 10, 50, 100 |
| Runs per configuration | 30 |
| Total configurations | 6 |
| Total HTTP requests | 180 |
| Percentile method | Linear interpolation |

## Results

| Version | Page size | Mean queries | Client p50 | Client p95 |
|---|---:|---:|---:|---:|
| Naive | 10 | 11.00 | 41.82 ms | 306.50 ms |
| Naive | 50 | 51.00 | 153.34 ms | 205.71 ms |
| Naive | 100 | 101.00 | 259.48 ms | 355.72 ms |
| Optimized | 10 | 2.00 | 17.02 ms | 34.62 ms |
| Optimized | 50 | 2.00 | 24.52 ms | 41.44 ms |
| Optimized | 100 | 2.00 | 24.48 ms | 38.27 ms |

## N+1 Interpretation

The naive implementation issued one query for the page of clinical trials and one additional query for every trial in that page.

Therefore:

- Page size 10 produced 11 queries.
- Page size 50 produced 51 queries.
- Page size 100 produced 101 queries.

The optimized implementation used SQLAlchemy `selectinload()` and completed every configuration using two queries:

1. One query for the clinical trials.
2. One query for all related trial sites.

At a page size of 100, the median client latency decreased from 259.48 ms to 24.48 ms.

The approximate median-latency reduction was:

```text
(259.48 - 24.48) / 259.48 × 100 = 90.57%