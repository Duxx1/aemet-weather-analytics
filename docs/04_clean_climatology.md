# 04 · Climatology Cleaning and Consolidation

## Context

The raw JSON files downloaded from AEMET are not ready for analysis. They contain empty and sparse records, inconsistent date formats, numeric values with embedded metadata in parentheses, and a schema that evolved over time, with newer records having more fields than older ones. This script applies a defined set of cleaning rules to all 158 raw files and consolidates them into two structured datasets: one for monthly records and one for annual summaries.

The cleaning decisions made here are directly informed by the findings of `validate_raw_data.py`.

**Position in the pipeline:**

```
ingestion → [filter stations] → [download climatology] → [validate_raw_data]
                                                                ↓
                                                      clean_climatology ← YOU ARE HERE
                                                                ↓
                                                         EDA / notebooks
```

---

## Script

`src/eda/clean_climatology.py`

### Usage

```bash
# Default paths
python src/eda/clean_climatology.py

# Custom paths
python src/eda/clean_climatology.py --input-dir data/raw/climatology/monthly --output-dir data/processed
```

The script must be run from the **project root** so that relative paths resolve correctly.

### Dependencies

Standard library: `json`, `re`, `argparse`, `pathlib`  
Third-party: `pandas`, `pyarrow` (required for Parquet export)

---

## Input

All `.json` files in `data/raw/climatology/monthly/` — 158 files covering 24 stations in the province of Badajoz, downloaded from AEMET's climatology endpoint in 3-year windows.

**Raw dataset summary (before cleaning):**

| Metric | Value |
|---|---|
| Files | 158 |
| Stations | 24 |
| Total records | 5,499 |
| Monthly records | 5,076 |
| Annual records | 423 |

---

## Cleaning steps

### 1. Load and tag

All JSON files are loaded into a single flat list of records. Each record is tagged with its source filename in a `_file` field for traceability during processing (this field is not written to the output).

### 2. Filter and split

Records are classified by date type and filtered before any cleaning is applied:

| Action | Condition | Count |
|---|---|---|
| Drop | Empty records (0 data fields) | 342 |
| Drop | Sparse monthly records (1–4 data fields) | 54 |
| Keep → monthly | `fecha` matches `YYYY-M` or `YYYY-MM` | 4,766 |
| Keep → annual | `fecha` matches `YYYY-13` | 337 |

Empty and sparse records are dropped because they contain insufficient data to be analytically useful. The sparse threshold (fewer than 5 fields) applies only to monthly records; annual summaries are not subject to it because their structure is inherently different.

### 3. Date normalisation

Monthly `fecha` values are normalized to zero-padded `YYYY-MM` format:

```
"2009-1"  →  "2009-01"
"2009-10" →  "2009-10"
```

Two derived columns are added to both datasets:

- `year` (integer) — extracted from `fecha`
- `month` (integer) — extracted from `fecha`, monthly dataset only

Annual records retain their original `fecha` value (`YYYY-13`) alongside the `year` column.

### 4. Wind gust splitting

AEMET encodes `w_racha` as a single string combining wind direction and gust speed:

```
"15/17.2(15)"     →  w_racha_dir = 15.0,  w_racha_spd = 17.2
"26/21.4(22/ene)" →  w_racha_dir = 26.0,  w_racha_spd = 21.4
```

Storing direction and speed in a single column is not analytically useful, so the field is split into two separate float columns. The split uses `split("/", 1)` to ensure that the slash inside the annual metadata parentheses — e.g. `(22/ene)` — does not interfere.

### 5. Metadata stripping

Several fields embed the day (and in annual summaries, the month) of occurrence alongside the measurement value:

```
"29.3(01)"     →  29.3   (monthly: day 1)
"53.2(29/oct)" →  53.2   (annual: 29th of October)
"0.0(--)"      →  0.0    (zero with no valid day)
```

The parenthesized content is stripped with a regex and only the numeric value is kept. Fields processed this way: `ta_max`, `ta_min`, `p_max`, `q_max`, `q_min`, `ts_min`, `ti_max`.

### 6. Numeric casting

All remaining numeric fields (stored as plain strings by AEMET) are cast to `float`. Fields absent in a given record are left as `NaN` rather than being dropped, preserving the full column schema across all records regardless of when they were recorded.

---

## Output

Two datasets are written to `data/processed/`, each in CSV and Parquet format:

### `climatology_monthly.csv / .parquet`

| Metric | Value |
|---|---|
| Rows | 4,766 |
| Columns | 42 |
| Coverage | Monthly records, one row per station per month |

Column order: `indicativo`, `fecha`, `year`, `month`, followed by all climatic fields.

### `climatology_annual.csv / .parquet`

| Metric | Value |
|---|---|
| Rows | 337 |
| Columns | 41 |
| Coverage | Annual summaries, one row per station per year |

Column order: `indicativo`, `fecha`, `year`, followed by all climatic fields. No `month` column.

### Key columns

| Column | Type | Description |
|---|---|---|
| `indicativo` | string | AEMET station identifier |
| `fecha` | string | Normalised date (`YYYY-MM` for monthly, `YYYY-13` for annual) |
| `year` | int | Calendar year |
| `month` | int | Calendar month (monthly dataset only) |
| `tm_mes` | float | Mean monthly temperature (°C) |
| `tm_max` | float | Mean of daily maximum temperatures (°C) |
| `tm_min` | float | Mean of daily minimum temperatures (°C) |
| `ta_max` | float | Absolute maximum temperature (°C) |
| `ta_min` | float | Absolute minimum temperature (°C) |
| `p_mes` | float | Total monthly precipitation (mm) |
| `p_max` | float | Maximum daily precipitation (mm) |
| `w_racha_dir` | float | Direction of maximum wind gust (degrees) |
| `w_racha_spd` | float | Speed of maximum wind gust (km/h) |
| `hr` | float | Mean relative humidity (%) |
| `inso` | float | Mean daily sunshine hours |

> NaN values are expected and intentional. AEMET expanded its published variables over time, so older records lack fields that are present in recent ones. This is not data corruption.

---

## Design decisions

**Why separate monthly and annual into different files?** Annual summaries have a different structure, different field semantics, and different analytical uses than monthly records. Mixing them in a single dataset would require constant filtering and would complicate every downstream step.

**Why drop sparse records instead of keeping them?** Records with fewer than 5 fields cannot meaningfully contribute to any multi-variable analysis. Keeping them would add rows that are almost entirely NaN, inflating missingness statistics without providing useful information.

**Why split `w_racha` into two columns?** Wind direction and wind speed are two independent measurements. Combining them in a single string column makes both values unusable for analysis without an additional parsing step. Splitting them during cleaning means downstream consumers get clean floats directly.

**Why use Parquet in addition to CSV?** CSV is human-readable and easy to inspect. Parquet preserves column types, is significantly faster to read in pandas, and produces smaller files. Both are included to support different workflows: quick inspection via CSV, and efficient loading in notebooks and Power BI via Parquet.

**Why not commit the output files to the repository?** The CSV and Parquet files in `data/processed/` are generated artefacts. Any collaborator can reproduce them by running this script on the raw data. Committing binary or large generated files to Git adds unnecessary repository size and creates merge conflicts with no benefit.

---

## Reproducing the output

```bash
# From the project root
python src/eda/clean_climatology.py
```

Expected output:

```
Loading 158 files from 'data/raw/climatology/monthly'...
Total records loaded: 5499

Filtering and splitting records...
  Dropped: 342 empty, 54 sparse, 0 invalid date
  Kept: 4766 monthly, 337 annual

Cleaning monthly records...
Cleaning annual records...

Exporting to 'data/processed'...
  Saved: data/processed/climatology_monthly.csv  (4766 rows, 42 columns)
  Saved: data/processed/climatology_monthly.parquet
  Saved: data/processed/climatology_annual.csv  (337 rows, 41 columns)
  Saved: data/processed/climatology_annual.parquet

Done.
```