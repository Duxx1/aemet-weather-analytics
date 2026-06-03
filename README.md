# AEMET Climatology · Data Pipeline

An end-to-end data project built as part of my data analyst / data engineer portfolio. It uses the [AEMET OpenData API](https://opendata.aemet.es/) to download, validate, clean, analyze, and persist historical climatology data for the province of **Badajoz, Spain**.

The goal is to demonstrate a complete, reproducible data workflow: API ingestion, raw data storage, quality validation, cleaning, exploratory analysis, relational persistence in PostgreSQL, and a final dashboard in Power BI with every step documented and traceable.

---

## Stack

- **Python**: pandas, requests, python-dotenv, pyarrow, matplotlib, seaborn, SQLAlchemy
- **PostgreSQL**: structured persistence using a star schema
- **Power BI**: final visualization layer (planned)
- **Git / GitHub**: version control with a Gitflow branching strategy

---

## Project structure

```
├── data/
│   └── raw/
│       ├── stations.json                       # Full AEMET station inventory
│       ├── badajoz_stations.json               # Filtered: Badajoz province only
│       ├── badajoz_stations_indicativos.json
│       └── climatology/
│           └── monthly/                        # Raw JSON files per station and time window
├── docs/                                       # Markdown documentation for each pipeline stage
│   ├── 00_variables_reference.md
│   ├── 01_data_extraction_aemet.md
│   ├── 02_download_climatology.md
│   ├── 03_validate_raw_data.md
│   ├── 04_clean_climatology.md
│   ├── 05_eda_climatology.md
│   └── 06_postgresql_load.md
├── notebooks/
│   └── eda_climatology.ipynb                   # Full exploratory data analysis
├── src/
│   ├── ingestion/
│   │   ├── aemet_downloader.py                 # Downloads station inventory
│   │   └── download_climatology.py             # Downloads monthly climatology per station
│   ├── processing/
│   │   └── filter_stations.py                  # Filters stations by province
│   ├── eda/
│   │   ├── validate_raw_data.py                # Quality check on raw JSON files
│   │   └── clean_climatology.py                # Cleans and consolidates into CSV/Parquet
│   └── load/
│       └── load_to_postgres.py                 # Loads cleaned data into PostgreSQL
├── sql/
│   └── schema.sql                              # PostgreSQL star schema definition
├── dashboard/                                  # Planned: Power BI assets
├── .env.example                                # Template for required environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

---

## How to run

### 1. Clone the repository

```bash
git clone https://github.com/Duxx1/aemet-weather-analytics.git
cd aemet-weather-analytics
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Get a free API key from [AEMET OpenData](https://opendata.aemet.es/centrodedescargas/altaUsuario).

Create a `.env` file in the project root:

```
AEMET_API_KEY=your_api_key_here

DB_HOST=localhost
DB_PORT=5432
DB_NAME=aemet_climatology
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 4. Run the data pipeline in order

```bash
# Download station inventory
python src/ingestion/aemet_downloader.py

# Filter stations by province
python src/processing/filter_stations.py

# Download climatology data (takes several minutes due to API rate limits)
python src/ingestion/download_climatology.py

# Validate raw data quality
python src/eda/validate_raw_data.py

# Clean and consolidate into structured datasets
python src/eda/clean_climatology.py
```

The cleaned datasets will be written to `data/processed/`:
- `climatology_monthly.csv / .parquet` — 4,766 monthly records
- `climatology_annual.csv / .parquet` — 337 annual summaries

> `data/processed/` is not tracked by Git. Run the pipeline to regenerate it locally.

### 5. Explore the data (optional)

```bash
jupyter notebook notebooks/eda_climatology.ipynb
```

### 6. Load into PostgreSQL

Create a database named `aemet_climatology`, then run the schema and the loader:

```bash
# Create the star schema (run sql/schema.sql against the database via psql or pgAdmin)
# Then load the data:
python src/load/load_to_postgres.py
```

---

## Data

- **Source:** [AEMET OpenData](https://opendata.aemet.es/) — Spain's national meteorological agency
- **Coverage:** 24 weather stations in the province of Badajoz
- **Period:** approximately 2000–2025
- **Granularity:** monthly climatology records per station, plus annual summaries

### Known data characteristics

- The AEMET API returns JSON with numeric values that embed day-of-occurrence metadata in parentheses (e.g. `"29.3(01)"`). These are stripped during cleaning.
- The wind gust field `w_racha` encodes both direction and speed in a single string (e.g. `"15/17.2(15)"`). It is split into `w_racha_dir` and `w_racha_spd` during cleaning.
- Wind direction is stored on a 1–36 scale (each unit = 10°), converted to compass degrees during cleaning.
- The API enforces a 36-month limit per request. Downloads are split into 3-year windows.
- Some records are empty or sparse (no observations published for that month). These are dropped during cleaning.
- The published schema expanded over time. Older records have fewer fields than recent ones. Missing fields are represented as `NaN`.

See `docs/00_variables_reference.md` for a full description of every variable.

---

## Pipeline status

| Stage | Script / artefact | Status |
|---|---|---|
| Station inventory | `aemet_downloader.py` | Done |
| Province filtering | `filter_stations.py` | Done |
| Climatology download | `download_climatology.py` | Done |
| Raw data validation | `validate_raw_data.py` | Done |
| Cleaning and consolidation | `clean_climatology.py` | Done |
| Exploratory data analysis | `eda_climatology.ipynb` | Done |
| PostgreSQL load | `load_to_postgres.py` + `schema.sql` | Done |
| Power BI dashboard | — | Planned |

---

## Key findings

A summary of the exploratory analysis (full details in `docs/05_eda_climatology.md`):

- **Temperature:** homogeneous Mediterranean-continental regime across the province, with a mild warming trend visible from 2010 onwards.
- **Precipitation:** high inter-annual variability (200–800 mm/year), dry summers, and rainfall concentrated in autumn-winter-spring. One station shows exceptional October rainfall linked to DANA events.
- **Wind:** strongest in spring, dominant gust directions from the north-northwest, west-northwest and south-southwest, reflecting Atlantic influence.

---

## Documentation

Each pipeline stage has a dedicated Markdown document in `docs/` explaining what the script does, how to use it, what the output looks like, and the design decisions made. These are intended for anyone, technical or non-technical, who wants to understand the project without reading the code.

---

## Author

Eduardo Cano (Duxx) — data analyst / data engineer / data scientist  
[GitHub](https://github.com/Duxx1) · [LinkedIn](https://linkedin.com/in/eduardo-cano-garcía-725650291)