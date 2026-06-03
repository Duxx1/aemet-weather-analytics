# 06 · PostgreSQL Load

## Context

The cleaned climatology datasets (CSV/Parquet) are well suited for analysis in pandas, but a relational database provides structured persistence, referential integrity, and a clean connection point for BI tools like Power BI. This stage loads the cleaned data into PostgreSQL following a star schema, separating descriptive dimensions from numeric measurements.

**Position in the pipeline:**

```
[clean_climatology] → [eda_climatology] → postgresql_load ← YOU ARE HERE
                                                 ↓
                                          Power BI dashboard
```

---

## Components

| File | Purpose |
|---|---|
| `sql/schema.sql` | Defines the star schema (tables, keys, indexes) |
| `src/load/load_to_postgres.py` | Reads cleaned data and loads it into the schema |

---

## Data model (star schema)

The design separates data into dimension tables (descriptive, slowly changing) and fact tables (numeric measurements, one row per observation).

```
                ┌──────────────────┐
                │   dim_station    │
                │──────────────────│
                │ indicativo (PK)  │
                │ nombre           │
                │ provincia        │
                │ altitud          │
                │ latitud          │
                │ longitud         │
                │ indsinop         │
                └────────┬─────────┘
                         │
         ┌───────────────┼───────────────┐
         │                               │
┌────────▼──────────────────┐  ┌─────────▼─────────────────┐
│ fact_climatology_monthly  │  │ fact_climatology_annual   │
│───────────────────────────│  │───────────────────────────│
│ id (PK)                   │  │ id (PK)                   │
│ indicativo (FK)           │  │ indicativo (FK)           │
│ date_id (FK) ─────┐       │  │ year                      │
│ tm_mes, p_mes ... │       │  │ tm_mes, p_mes ...         │
└───────────────────┼───────┘  └───────────────────────────┘
                    │
           ┌────────▼─────────┐
           │    dim_date      │
           │──────────────────│
           │ date_id (PK)     │
           │ year             │
           │ month            │
           │ month_name       │
           │ season           │
           └──────────────────┘
```

### dim_station

One row per weather station. 24 rows.

| Column | Type | Description |
|---|---|---|
| `indicativo` | TEXT (PK) | AEMET station code |
| `nombre` | TEXT | Station name |
| `provincia` | TEXT | Province |
| `altitud` | INTEGER | Altitude (m) |
| `latitud` | DOUBLE PRECISION | Decimal degrees |
| `longitud` | DOUBLE PRECISION | Decimal degrees (negative for West) |
| `indsinop` | TEXT | WMO synoptic index |

### dim_date

One row per year-month present in the data. 312 rows.

| Column | Type | Description |
|---|---|---|
| `date_id` | INTEGER (PK) | Format YYYYMM (e.g. 200910) |
| `year` | INTEGER | |
| `month` | INTEGER | |
| `month_name` | TEXT | "January", etc. |
| `season` | TEXT | Meteorological season |

### fact_climatology_monthly

One row per station-month. 4,766 rows. References both dimensions.

### fact_climatology_annual

One row per station-year. 337 rows. References dim_station.

Both fact tables share the same measurement columns: temperature (`tm_mes`, `tm_max`, `tm_min`, `ta_max`, `ta_min`), precipitation (`p_mes`, `p_max`), wind (`w_med`, `w_racha_spd`, `w_racha_dir`), humidity (`hr`), and day counters (`nt_30`, `nt_00`).

---

## Setup

### 1. Create the database

In pgAdmin (or psql), create a database named `aemet_climatology`.

### 2. Configure credentials

Add the database connection variables to `.env`:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aemet_climatology
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Install dependencies

```bash
pip install sqlalchemy psycopg2-binary
```

### 4. Create the schema

Run `sql/schema.sql` against the database. It drops any existing tables and recreates them from scratch, so it is safe to re-run during development.

---

## Usage

```bash
python src/load/load_to_postgres.py
```

The script is **idempotent**: it truncates all tables before loading, so it can be run repeatedly and always leaves the database in the same state.

Expected output:

```
Reading source data...
Building dimension and fact tables...

Truncating existing data...
Existing tables truncated.

Loading into PostgreSQL...
  Loaded 24 rows into dim_station
  Loaded 312 rows into dim_date
  Loaded 4766 rows into fact_climatology_monthly
  Loaded 337 rows into fact_climatology_annual

Done.
```

---

## Key processing steps

### Coordinate conversion

AEMET stores coordinates in degrees-minutes-seconds with an orientation letter:

```
"391010N" -> 39° 10' 10" North -> 39.169
"050344W" ->  5° 03' 44" West  -> -5.062
```

The `dms_to_decimal` function parses this format with a regex and applies:

```
decimal = degrees + minutes/60 + seconds/3600
```

South and West orientations produce negative values. This makes the coordinates usable directly in Power BI map visuals.

### Date dimension generation

The `date_id` is derived as `year * 100 + month`, producing a sortable integer key (e.g. 200910). Month names and meteorological seasons are derived programmatically.

### Referential integrity

Before loading the fact tables, the script filters records to keep only stations that exist in `dim_station`. This guarantees that every foreign key in the fact tables points to a valid dimension row, preventing constraint violations.

### Load order

Tables are loaded dimensions-first, then facts. This is required because the fact tables have foreign keys referencing the dimensions; a fact row cannot be inserted before the station and date it references exist.

---

## Design decisions

**Why a star schema instead of a single flat table?** Separating descriptive attributes (station metadata, date attributes) from measurements avoids repeating the same station name or coordinates across hundreds of rows. It is the standard model for analytical workloads and integrates cleanly with BI tools.

**Why a surrogate `id` (SERIAL) in the fact tables?** There is no single natural column that uniquely identifies a fact row, so an auto-incremented surrogate key is used as the primary key. The natural uniqueness (one row per station-month) is enforced separately with a `UNIQUE` constraint.

**Why make the script idempotent with TRUNCATE?** During development the script is run repeatedly. Truncating before loading avoids primary-key and unique-constraint violations from duplicate inserts, and guarantees a clean, reproducible state every time.

**Why indexes on station and date columns?** Power BI and ad-hoc queries will frequently filter by station or time period. Indexes on these columns speed up those queries significantly compared to scanning the full table.

