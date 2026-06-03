"""
Loads the cleaned climatology datasets and station metadata into PostgreSQL,
populating a star schema (dim_station, dim_date, fact_climatology_monthly, fact_climatology_annual).

Prerequisites:
    - PostgreSQL running with the database and schema already created (sql/schema.sql)
    - Connection credentials defined in .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    - Cleaned datasets present in data/processed/

Usage:
    python src/load/load_to_postgres.py
"""

import os
import json
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Configuration

PROCESSED_DIR = Path("data/processed")
STATIONS_FILE = Path("data/raw/badajoz_stations.json")

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# Columns the fact tables expect (must match the schema)
FACT_COLUMNS = [
    "tm_mes", "tm_max", "tm_min", "ta_max", "ta_min",
    "p_mes", "p_max",
    "w_med", "w_racha_spd", "w_racha_dir",
    "hr", "nt_30", "nt_00",
]


# Database connection

def get_engine():
    """Builds a SQLAlchemy engine from environment variables."""
    
    load_dotenv()
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

    return create_engine(url)


# Coordinate conversion

def dms_to_decimal(coord: str) -> float | None:
    """
    Converts an AEMET coordinate string to decimal degrees.

    Format: DDMMSS + orientation letter (N/S/E/W).
        "391010N" -> 39 + 10/60 + 10/3600 = 39.169  (North, positive)
        "050344W" -> -(5 + 3/60 + 44/3600) = -5.062  (West, negative)

    Returns None if the format is not recognised.
    """

    if not isinstance(coord, str):
        return None

    match = re.match(r"^(\d{2,3})(\d{2})(\d{2})([NSEW])$", coord)
    if not match:
        return None

    degrees, minutes, seconds, orientation = match.groups()
    decimal = int(degrees) + int(minutes) / 60 + int(seconds) / 3600

    # South and West are negative
    if orientation in ("S", "W"):
        decimal = -decimal

    return round(decimal, 6)


# Build dimension and fact dataframes

def build_dim_station(stations_file: Path) -> pd.DataFrame:
    """Reads the station metadata JSON and builds the station dimension."""
    
    with open(stations_file, encoding="utf-8") as f:
        stations = json.load(f)

    rows = []
    for s in stations:
        rows.append({
            "indicativo": s["indicativo"],
            "nombre": s["nombre"],
            "provincia": s["provincia"],
            "altitud": int(s["altitud"]) if s.get("altitud") else None,
            "latitud": dms_to_decimal(s.get("latitud", "")),
            "longitud": dms_to_decimal(s.get("longitud", "")),
            "indsinop": s.get("indsinop"),
        })

    return pd.DataFrame(rows)


def build_dim_date(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """Builds the date dimension from the unique year-month combinations."""
    
    dates = df_monthly[["year", "month"]].drop_duplicates().copy()

    dates["date_id"] = dates["year"] * 100 + dates["month"]  # e.g. 2009*100+10 = 200910
    dates["month_name"] = dates["month"].map(MONTH_NAMES)
    dates["season"] = dates["month"].map(month_to_season)

    return dates[["date_id", "year", "month", "month_name", "season"]]


def month_to_season(month: int) -> str:
    """Maps a month number to its meteorological season (Northern Hemisphere)."""
    
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    
    return "Autumn"


def build_fact_monthly(df_monthly: pd.DataFrame, valid_stations: set) -> pd.DataFrame:
    """Prepares the monthly fact table dataframe."""
    
    df = df_monthly.copy()
    df["date_id"] = df["year"] * 100 + df["month"]

    # Keep only stations that exist in the dimension (referential integrity)
    df = df[df["indicativo"].isin(valid_stations)]

    # Keep only columns the fact table expects, adding missing ones as NaN
    keep = ["indicativo", "date_id"] + FACT_COLUMNS
    for col in FACT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    return df[keep]


def build_fact_annual(df_annual: pd.DataFrame, valid_stations: set) -> pd.DataFrame:
    """Prepares the annual fact table dataframe."""
    
    df = df_annual.copy()
    df = df[df["indicativo"].isin(valid_stations)]

    keep = ["indicativo", "year"] + FACT_COLUMNS
    for col in FACT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    
    return df[keep]


# Empty all tables before loading

def truncate_tables(engine) -> None:
    """
    Empties all tables before loading, making the script idempotent.
    Order respects foreign keys: facts first, then dimensions.
    RESTART IDENTITY resets the SERIAL counters.
    """

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE fact_climatology_monthly, fact_climatology_annual, "
            "dim_date, dim_station RESTART IDENTITY CASCADE"
        ))

    print("Existing tables truncated.")

# Load into PostgreSQL

def load_table(engine, df: pd.DataFrame, table_name: str) -> None:
    """Appends a dataframe to an existing table."""
    
    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f"  Loaded {len(df)} rows into {table_name}")


def main():
    engine = get_engine()

    # Load source data
    print("Reading source data...")
    df_monthly = pd.read_parquet(PROCESSED_DIR / "climatology_monthly.parquet")
    df_annual = pd.read_parquet(PROCESSED_DIR / "climatology_annual.parquet")

    # Build dataframes
    print("Building dimension and fact tables...")
    dim_station = build_dim_station(STATIONS_FILE)
    dim_date = build_dim_date(df_monthly)

    valid_stations = set(dim_station["indicativo"])
    fact_monthly = build_fact_monthly(df_monthly, valid_stations)
    fact_annual = build_fact_annual(df_annual, valid_stations)

    # Empty tables first so the script can be run repeatedly
    print("\nTruncating existing data...")
    truncate_tables(engine)

    # Load in dependency order: dimensions first, then facts
    print("\nLoading into PostgreSQL...")
    load_table(engine, dim_station, "dim_station")
    load_table(engine, dim_date, "dim_date")
    load_table(engine, fact_monthly, "fact_climatology_monthly")
    load_table(engine, fact_annual, "fact_climatology_annual")

    print("\nDone.")


if __name__ == "__main__":
    main()