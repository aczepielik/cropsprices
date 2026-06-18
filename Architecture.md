# Crops Prices Tracking App Architecture

This document describes the current architecture of the crops prices tracking application.

## Overview

The application follows a loosely decoupled ETL-Storage-App architecture, utilizing Google Cloud Platform (GCP) services and embedded DuckDB for data processing and serving.

---

## 1. ETL Layer (Data Ingestion & Processing)

The ETL process is currently implemented as a set of Python scripts intended for initialization and bulk processing.

### Phase 1: Data Discovery & Raw Ingestion
- **Tool:** `scripts/etl/bulk_get_resources.py`
- **Source:** [api.dane.gov.pl](https://api.dane.gov.pl)
- **Actions:**
    1. Queries the API for bulletins related to "ceny hurtowe i targowiskowe".
    2. Stores resource metadata in BigQuery (`cropsprices_core.resources`).
    3. Downloads raw `.xlsx` workbooks and uploads them to Google Cloud Storage (GCS) under the `wholesale_prices_workbooks/` prefix.

### Phase 2: Data Parsing & Structured Storage
- **Tool:** `scripts/etl/bulk_process_resources.py`
- **Logic:** `cropsprices/parsers.py`
- **Actions:**
    1. Lists `.xlsx` files from GCS.
    2. Parses "vegetables" and "fruits" sheets from each workbook.
    3. Handles inconsistent Excel formats (different sheet names, header locations, units).
    4. Inserts parsed price data into BigQuery tables:
        - `wholesale_prices_vegetables`
        - `wholesale_prices_fruits`

### Phase 3: Analytical Export
- **Tool:** `scripts/export_bqtables_to_parquet.py`
- **Actions:**
    1. Exports BigQuery tables to Parquet format in GCS (`gs://{bucket}/exports/`).
    2. This step enables the application to use DuckDB for efficient querying without direct BigQuery dependency in all environments.

---

## 2. Storage Layer (Redundant Storage)

Data is redundantly stored across three systems:

1.  **Google Cloud Storage (GCS):**
    - Raw `.xlsx` bulletins (Source of truth for ingestion).
    - Exported `.parquet` files (Optimized for application access).
2.  **BigQuery:**
    - `resources`: Metadata about downloaded bulletins.
    - `wholesale_prices_vegetables`/`fruits`: Structured price data (Primary analytical store).
3.  **DuckDB:**
    - Used as an embedded database within the application.
    - In **Cloud** environments, it uses the `httpfs` extension to query Parquet files directly from GCS via HMAC credentials.
    - In **Dev** environment, it uses a local `.db` file.

---

## 3. Application Layer (NiceGUI App)

The frontend is a Python-based web application built with **NiceGUI**.

- **Entry Point:** `app/main.py`
- **UI Components:** Defined in `app/ui_components.py`.
- **Database Management:** `app/database.py` handles switching between DuckDB (local/cloud) and BigQuery based on environment.
- **Features:**
    - Filter by product type (vegetables/fruits), origin (domestic/imported), market place, and date.
    - Year-over-year price comparison (calculated via SQL views in `app/db_views.sql`).
    - Interactive price charts using Matplotlib.

---

## 4. Deployment & Infrastructure

### Hosting
- **Cloud Run:** The NiceGUI application is containerized and deployed to Google Cloud Run.
- **Docker:** `Dockerfile` defines a multi-stage build, including DuckDB CLI and necessary fonts for Matplotlib.

### CI/CD
- **Cloud Build:** `cloudbuild.yaml` handles the build and deployment pipeline.
- **Environments:**
    - `dev`: Local development, uses local DuckDB.
    - `staging`: Deployed to Cloud Run, uses `CloudDuckDBConnector` reading from `exports/`.
    - `prod`: Deployed to Cloud Run, uses `CloudDuckDBConnector` reading from `exports/latest/`.

### Configuration & Secrets
- **Secret Manager:** Stores sensitive information like GCS bucket names and HMAC credentials.
- **Environment Variables:** Managed via `.env` files and Cloud Run configuration.

---

## Architectural Challenges & Redundancy

1.  **Data Redundancy:** Data exists in GCS (raw), BigQuery (structured), and GCS (parquet).
2.  **Manual Steps:** The transition from BigQuery to Parquet and the movement of files to `/latest` seems to be partially manual or script-driven rather than fully automated in a pipeline.
3.  **Hybrid DB Access:** The application can query both BigQuery and DuckDB, leading to dual maintenance of SQL logic (e.g., `app/database.py` abstraction layer).

---

## Original motivations

1. **Cloud:** The intial idea was to host the app in such a way that under assumption of very low traffic the cost is near zero. Hence BigQuery (contrary to managed Postgres it has free quota), Cloud Run (paying only ofr actual usage, not for idleness), cloud storage (very cheap)

2. **Embedded DuckDB:** First it was just a convienience tool for local development. When it turned out that BQ has too big latency it became part of the production

3. **NiceGUI:** I don't know JS/TS but know python so opted for it. Plus it has nice wrapper around matplotlib.

## Critique

1. **Cloud:** Due to misconfiguration of Cloud Function which was supposed to hydrate the databse I made millions of failed queries to BQ (the said function was retrying on eah fail hence looping errors) which costed me huge money. When I got an alert it was too late.

2. **Embedded DuckDB:** Does the job but complicates things a lot

3. **NiceGUI:** Debugging async python wrapper for JS turned out as complicated as if it was a foreign language