# 03 · Raw Data Validation

## Context

Before cleaning or analyzing anything, it is necessary to understand the actual state of the raw data. AEMET's API returns JSON files whose structure is inconsistent across stations and time periods: some records are completely empty, others have only a handful of fields, numeric values embed day-of-occurrence metadata in parentheses, and annual summaries follow a different format than monthly ones.

This script runs a systematic quality check across all downloaded JSON files and produces a structured report that drives the cleaning decisions in the next phase.

**Position in the pipeline:**

```
ingestion → [filter stations] → [download climatology] → validate_raw_data ← YOU ARE HERE
                                                                ↓
                                                        clean_climatology
```

---

## Script

`src/eda/validate_raw_data.py`

### Usage

```bash
# Terminal report only
python src/eda/validate_raw_data.py

# Terminal report + detailed CSV export
python src/eda/validate_raw_data.py --output data/interim/validation_report.csv

# Custom input directory
python src/eda/validate_raw_data.py --dir data/raw/climatology/monthly --output data/interim/validation_report.csv
```

The script must be run from the **project root** so that relative paths resolve correctly.

### Dependencies

Standard library: `json`, `re`, `argparse`, `pathlib`, `collections`  
Third-party: `pandas`

---

## Input

All `.json` files found in `data/raw/climatology/monthly/` (or the directory passed via `--dir`).

Each file follows the naming convention `{indicativo}_{start_year}_{end_year}.json` and contains a JSON array of climatology records, one object per month (and one per year for annual summaries).

Example of a complete monthly record:

```json
{
  "indicativo": "4244X",
  "fecha": "2024-10",
  "tm_mes": "17.5",
  "tm_max": "22.3",
  "tm_min": "12.8",
  "ta_max": "29.3(01)",
  "ta_min": "6.5(27)",
  "p_mes": "173.6",
  "p_max": "53.2(29)",
  "hr": "67",
  "w_racha": "15/17.2(15)",
  ...
}
```

Example of an empty record (no observations for that month):

```json
{"indicativo": "4244X", "fecha": "2001-1"}
```

---

## What the script checks

### 1. Date classification

Each `fecha` value is classified into one of three categories:

| Category | Pattern | Meaning |
|---|---|---|
| `mensual` | `YYYY-M` or `YYYY-MM` | Standard monthly record |
| `anual` | `YYYY-13` | Annual summary (AEMET encodes year-level aggregates with month = 13) |
| `invalida` | anything else | Unexpected format |

Month values without a leading zero (e.g. `2009-1`) are accepted as valid — this is an AEMET quirk, not a data error.

### 2. Empty records

Records containing only `indicativo` and `fecha` with no data fields. These represent months where AEMET holds no published observations for that station.

### 3. Sparse records

Monthly records with between 1 and 4 data fields. These have some data but not enough to be analytically useful for most variables.

### 4. Non-numeric values in numeric fields

Fields like `hr`, `tm_mes`, `p_mes` or `w_rec` should always be plain numbers stored as strings. The script attempts `float()` conversion and flags any failure.

### 5. Unparseable values in metadata-embedded fields

AEMET encodes auxiliary information alongside numeric values using parentheses:

| Format | Example | Meaning |
|---|---|---|
| `value(day)` | `"29.3(01)"` | Value and day of occurrence |
| `direction/speed(day)` | `"15/17.2(15)"` | Wind gust: direction in degrees, speed, day |
| `0.0(--)` | `"0.0(--)"` | Explicit zero, no valid day |
| `value(day/month)` | `"53.2(29/oct)"` | Annual summary: value with day and month |

The `extract_numeric` function strips this metadata and extracts only the base numeric value. It handles `w_racha` specifically by splitting on the **first** slash only (to separate direction from speed before stripping the rest), which correctly handles the annual format `"26/21.4(22/ene)"`.

Any value that still can not be converted to float after this process is flagged as `unexpected_format`.

---

## Output

### Terminal report

```
============================================================
VALIDATION REPORT - RAW CLIMATOLOGY
============================================================
  Files processed       : 158
  Unique stations       : 24
  Total records         : 5499
  Monthly records       : 5076
  Annual records        : 423
  Invalid dates         : 0
  Empty records         : 342
  Sparse records        : 54
  Records with issues   : 396 (7.2%)

  Avg fields per monthly record (non-empty): 23.8
  Field count distribution (non-empty monthly records):
       1-5 fields:    56 records
      6-10 fields:    81 records
     11-15 fields:   305 records
     16-20 fields:   313 records
     21-30 fields:  3578 records
       31+ fields:   487 records

  Issue type breakdown:
    empty_record                       : 342
    sparse_record                      : 54
============================================================
```

### CSV export (optional)

When `--output` is provided, a CSV is written with one row per record and the following columns:

| Column | Description |
|---|---|
| `indicativo` | Station identifier |
| `fecha` | Raw date string from AEMET |
| `date_type` | `mensual`, `anual`, or `invalida` |
| `n_fields` | Number of data fields present (excluding `indicativo` and `fecha`) |
| `issues` | Semicolon-separated list of detected issues, empty string if none |
| `has_issues` | Boolean flag |
| `_file` | Source JSON filename |

This CSV feeds directly into the cleaning phase, where it can be used to filter out empty or sparse records before building the consolidated dataset.

---

## Results interpretation

### On this dataset (158 files, 24 stations, Badajoz province)

- **5076 monthly records** and **423 annual summaries** — the totals are consistent with the download windows used (3-year chunks from 2001 to 2025 across 24 stations).
- **0 invalid dates** — all `fecha` values are recognisable by the classifier. The leading-zero-free format (`YYYY-M`) is handled correctly.
- **342 empty records (6.2%)** — months with no published data. These will be dropped during cleaning.
- **54 sparse records (1.0%)** — months with 1–4 fields. Depending on which fields are present, some may still be usable for specific variables.
- **No unexpected format issues** — all numeric and metadata-embedded fields parse correctly after accounting for AEMET's encoding conventions.
- **Field count distribution** — the majority of records (3578) have 21–30 fields, which corresponds to the standard modern schema. The 487 records with 31+ fields are from 2024–2025, which include additional fields (`inso`, `n_llu`, `n_tor`, `n_nie`, `nv_*`) not present in older data.

### Schema evolution across years

Older records (pre-2015 approximately) have fewer fields than recent ones. This is not data corruption, as AEMET has expanded its published variables over time. The cleaning script must handle this gracefully by accepting `NaN` for fields absent in older records rather than treating them as errors.

---

## Design decisions

**Why validate before cleaning?** Running a structured quality check first gives a precise picture of what needs to be handled and why. It avoids building a cleaning script that makes undocumented assumptions about the data it receives.

**Why separate `NUMERIC_FIELDS` from `FIELDS_WITH_METADATA`?** The two groups require different validation logic. Treating them the same would either produce false positives (flagging valid parenthesised values as errors) or false negatives (accepting malformed plain numbers without checking).

**Why keep `date_type` values in Spanish (`mensual`, `anual`, `invalida`)?** These are domain-level categories derived directly from AEMET's encoding conventions (specifically, month 13 for annual summaries). Keeping them in Spanish makes them easier to correlate with AEMET's own documentation and with field names in the dataset, which are also in Spanish.

**Why exclude `empty_record` and `sparse_record` from the "notable issues" sample?** These are expected and numerically dominant — including them would drown out any genuine format problems. The sample section is reserved for unexpected issues that require investigation.

**Why `split("/", 1)` for `w_racha`?** Annual summaries encode `w_racha` as `"26/21.4(22/ene)"`, which contains two slashes: one separating direction from speed, and one inside the day-month metadata within the parentheses. Using `split("/", 1)` ensures only the first slash is used as a separator, producing `["26", "21.4(22/ene)"]`, from which the speed can be correctly extracted.
