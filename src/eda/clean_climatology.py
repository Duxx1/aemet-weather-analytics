"""
clean_climatology.py
--------------------
Consolidates and cleans all raw climatology JSON files downloaded from AEMET.

Reads all JSON files from data/raw/climatology/monthly/, applies cleaning rules
informed by validate_raw_data.py, and exports two normalized datasets:
  - data/processed/climatology_monthly.csv / .parquet
  - data/processed/climatology_annual.csv  / .parquet

Cleaning steps applied:
  1. Drop empty records (no data fields) and sparse records (1-4 data fields)
  2. Separate monthly records (month 1-12) from annual summaries (month 13)
  3. Normalize fecha to zero-padded YYYY-MM; extract year and month as integers
  4. Split w_racha into w_racha_dir (degrees) and w_racha_spd (float)
  5. Strip day-of-occurrence metadata from parenthesised fields (e.g. "29.3(01)" -> 29.3)
  6. Cast all numeric columns to float

Usage:
    python src/eda/clean_climatology.py
    python src/eda/clean_climatology.py --input-dir data/raw/climatology/monthly
    python src/eda/clean_climatology.py --input-dir data/raw/climatology/monthly --output-dir data/processed
"""

import json
import re
import argparse
import pandas as pd
from pathlib import Path

# Configuration

RAW_DIR = Path("data/raw/climatology/monthly")
PROCESSED_DIR = Path("data/processed")

# Minimum number of data fields a monthly record must have to be kept.
# Records below this threshold are considered too sparse to be useful.
MIN_FIELDS_MONTHLY = 5

# Fields stored as plain numeric strings with no embedded metadata
NUMERIC_FIELDS = {
    "hr", "w_rec", "w_med", "e",
    "tm_mes", "tm_max", "tm_min", "ti_max",
    "ts_min", "p_mes",
    "nw_55", "nw_91", "nt_30", "nt_00",
    "np_001", "np_010", "np_100", "np_300",
    "n_cub", "n_des", "n_nub", "n_llu", "n_tor", "n_nie",
    "inso", "p_sol",
    "q_med", "q_mar",
    "nv_0050", "nv_0100", "nv_1000",
}

# Fields that embed day-of-occurrence (and optionally month) metadata in parentheses.
# w_racha is handled separately because it also embeds wind direction.
FIELDS_WITH_METADATA = {
    "ta_max", "ta_min", "p_max", "q_max", "q_min", "ts_min", "ti_max",
}

# Regex patterns
PATTERN_MONTHLY_DATE = re.compile(r"^\d{4}-(0?[1-9]|1[0-2])$")
PATTERN_ANNUAL_DATE = re.compile(r"^\d{4}-13$")
PATTERN_NULL_VALUE = re.compile(r"^0\.0\(--\)$")


# Parsing helpers

def classify_date(fecha: str) -> str:
    """Returns 'mensual', 'anual', or 'invalida'."""

    if PATTERN_ANNUAL_DATE.match(fecha):
        return "anual"
    if PATTERN_MONTHLY_DATE.match(fecha):
        return "mensual"
    return "invalida"


def strip_metadata(value: str) -> float | None:
    """
    Extracts the base numeric value from a parenthesised AEMET string.

    Examples:
        "29.3(01)"     -> 29.3
        "0.0(--)"      -> 0.0
        "53.2(29/oct)" -> 53.2  (annual summary format)

    Returns None if the value cannot be parsed.
    """

    if not isinstance(value, str):
        return None
    if PATTERN_NULL_VALUE.match(value.strip()):
        return 0.0
    clean = re.sub(r"\([^)]*\)", "", value).strip()
    try:
        return float(clean)
    except ValueError:
        return None


def parse_w_racha(value: str) -> tuple[float | None, float | None]:
    """
    Splits a w_racha string into direction and speed.

    AEMET format: "direction/speed(day)" or "direction/speed(day/month)"
    Examples:
        "15/17.2(15)"      -> (15.0, 17.2)
        "26/21.4(22/ene)"  -> (26.0, 21.4)  (annual summary)

    Returns (direction_degrees, speed) or (None, None) if unparseable.
    """
    if not isinstance(value, str):
        return None, None

    # Split on the first slash only to separate direction from the rest
    parts = value.split("/", 1)
    if len(parts) != 2:
        return None, None

    try:
        # AEMET encodes direction as a 1-36 scale (each unit = 10 degrees)
        direction = float(parts[0].strip()) * 10
    except ValueError:
        direction = None

    # Strip parenthesised metadata from the speed part
    speed = strip_metadata(parts[1])
    
    return direction, speed


def normalize_fecha_monthly(fecha: str) -> str:
    """
    Normalizes a monthly fecha string to zero-padded YYYY-MM format.

    "2009-1"  -> "2009-01"
    "2009-10" -> "2009-10"
    """

    year, month = fecha.split("-")

    return f"{year}-{int(month):02d}"


# Record-level cleaning
def clean_record(record: dict) -> dict:
    """
    Applies all cleaning transformations to a single raw record.

    Returns a new dict with:
        - fecha normalized (monthly records only)
        - year and month extracted as integers
        - w_racha split into w_racha_dir and w_racha_spd
        - metadata stripped from parenthesized fields
        - all numeric fields casted to float where present
    """

    # Output dict
    cleaned = {
        "indicativo": record.get("indicativo"),
        "fecha": record.get("fecha", ""),
    }

    raw_fecha = cleaned["fecha"]
    date_type = classify_date(raw_fecha)

    # Normalize fecha and extract time components
    if date_type == "mensual":
        cleaned["fecha"] = normalize_fecha_monthly(raw_fecha)
        year_str, month_str = raw_fecha.split("-")
        cleaned["year"] = int(year_str)
        cleaned["month"] = int(month_str)
    elif date_type == "anual":
        year_str = raw_fecha.split("-")[0]
        cleaned["year"] = int(year_str)
        # Keep fecha as is for annual records (YYYY-13); year column is the primary key

    # Split w_racha into direction and speed
    if "w_racha" in record:
        direction, speed = parse_w_racha(record["w_racha"])
        cleaned["w_racha_dir"] = direction
        cleaned["w_racha_spd"] = speed

    # Strip metadata from parenthesised fields
    for field in FIELDS_WITH_METADATA:
        if field in record:
            cleaned[field] = strip_metadata(record[field])

    # Cast plain numeric fields
    for field in NUMERIC_FIELDS:
        if field in record:
            try:
                cleaned[field] = float(record[field])
            except (ValueError, TypeError):
                cleaned[field] = None

    return cleaned


# Load and filter
def load_all_records(raw_dir: Path) -> list[dict]:
    """
    Loads all JSON files in raw_dir and returns a flat list of raw records,
    each tagged with its source filename.
    """
    all_records = []
    files = sorted(raw_dir.glob("*.json"))
    print(f"Loading {len(files)} files from '{raw_dir}'...")

    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: could not read '{path.name}': {e}")
            continue

        if not isinstance(data, list):
            print(f"  WARNING: '{path.name}' is not a JSON array, skipping.")
            continue

        for record in data:
            record["_file"] = path.name
        all_records.extend(data)

    return all_records


def split_and_filter(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Classifies records by date type, drops empty/sparse/invalid records,
    and returns (monthly_records, annual_records).
    """

    monthly, annual = [], []
    dropped_empty = dropped_sparse = dropped_invalid = 0

    for record in records:
        fecha = record.get("fecha", "")
        date_type = classify_date(fecha)

        if date_type == "invalida":
            dropped_invalid += 1
            continue

        # Count data fields excluding identifiers
        data_fields = set(record.keys()) - {"indicativo", "fecha", "_file"}
        n_fields = len(data_fields)

        if n_fields == 0:
            dropped_empty += 1
            continue

        if date_type == "mensual" and n_fields < MIN_FIELDS_MONTHLY:
            dropped_sparse += 1
            continue

        if date_type == "mensual":
            monthly.append(record)
        else:
            annual.append(record)

    print(f"  Dropped: {dropped_empty} empty, {dropped_sparse} sparse, {dropped_invalid} invalid date")
    print(f"  Kept: {len(monthly)} monthly, {len(annual)} annual")

    return monthly, annual


# Build and export DataFrames
def build_dataframe(records: list[dict]) -> pd.DataFrame:
    """Cleans each record and assembles the results into a DataFrame."""

    cleaned = [clean_record(r) for r in records]

    return pd.DataFrame(cleaned)


def reorder_columns(df: pd.DataFrame, priority: list[str]) -> pd.DataFrame:
    """Moves priority columns to the front; remaining columns follow original order."""

    existing_priority = [c for c in priority if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_priority]

    return df[existing_priority + remaining]


def export_dataset(df: pd.DataFrame, output_dir: Path, name: str) -> None:
    """Exports a DataFrame to both CSV and Parquet under output_dir."""

    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{name}.csv"
    parquet_path = output_dir / f"{name}.parquet"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_parquet(parquet_path, index=False)

    print(f"  Saved: {csv_path}  ({len(df)} rows, {len(df.columns)} columns)")
    print(f"  Saved: {parquet_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Cleans and consolidates raw AEMET climatology JSON files."
    )
    parser.add_argument(
        "--input-dir", default=str(RAW_DIR),
        help="Directory containing raw JSON files (default: data/raw/climatology/monthly)"
    )
    parser.add_argument(
        "--output-dir", default=str(PROCESSED_DIR),
        help="Directory for output files (default: data/processed)"
    )
    args = parser.parse_args()

    raw_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not raw_dir.exists():
        print(f"ERROR: Input directory '{raw_dir}' does not exist.")
        return

    # Load
    all_records = load_all_records(raw_dir)
    print(f"Total records loaded: {len(all_records)}")

    # Filter and split
    print("\nFiltering and splitting records...")
    monthly_records, annual_records = split_and_filter(all_records)

    # Build DataFrames
    print("\nCleaning monthly records...")
    df_monthly = build_dataframe(monthly_records)
    df_monthly = reorder_columns(df_monthly, ["indicativo", "fecha", "year", "month"])

    print("Cleaning annual records...")
    df_annual = build_dataframe(annual_records)
    df_annual = reorder_columns(df_annual, ["indicativo", "fecha", "year"])

    # Export
    print(f"\nExporting to '{output_dir}'...")
    export_dataset(df_monthly, output_dir, "climatology_monthly")
    export_dataset(df_annual, output_dir, "climatology_annual")

    print("\nDone.")


if __name__ == "__main__":
    main()