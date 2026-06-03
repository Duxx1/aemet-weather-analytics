-- Star schema for AEMET climatology data (Badajoz province).
--
-- Structure:
--   dim_station              : one row per weather station (metadata)
--   dim_date                 : one row per year-month present in the data
--   fact_climatology_monthly : monthly measurements, references both dimensions
--   fact_climatology_annual  : annual summary measurements, references dim_station
--
-- Run order: this file creates all tables. Drop statements are included at the
-- top so the script can be re-run cleanly during development.
-- ----------------------------------------------------------------------------

-- Drop existing tables (children first, then parents, to respect foreign keys)
DROP TABLE IF EXISTS fact_climatology_monthly;
DROP TABLE IF EXISTS fact_climatology_annual;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_station;


-- ----------------------------------------------------------------------------
-- Dimension: stations
-- ----------------------------------------------------------------------------
CREATE TABLE dim_station (
    indicativo   TEXT PRIMARY KEY,        -- AEMET station code, unique identifier
    nombre       TEXT NOT NULL,           -- Human-readable station name
    provincia    TEXT NOT NULL,
    altitud      INTEGER,                 -- Altitude in metres
    latitud      DOUBLE PRECISION,        -- Decimal degrees (converted from AEMET format)
    longitud     DOUBLE PRECISION,        -- Decimal degrees (negative for West)
    indsinop     TEXT                     -- WMO synoptic index
);


-- ----------------------------------------------------------------------------
-- Dimension: dates (year-month)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_date (
    date_id      INTEGER PRIMARY KEY,     -- Format YYYYMM, e.g. 200910
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    month_name   TEXT NOT NULL,           -- "January", "February", ...
    season       TEXT NOT NULL            -- "Winter", "Spring", "Summer", "Autumn"
);


-- ----------------------------------------------------------------------------
-- Fact: monthly climatology
-- ----------------------------------------------------------------------------
CREATE TABLE fact_climatology_monthly (
    id           SERIAL PRIMARY KEY,      -- Surrogate key, auto-incremented
    indicativo   TEXT NOT NULL REFERENCES dim_station(indicativo),
    date_id      INTEGER NOT NULL REFERENCES dim_date(date_id),

    -- Temperature (Celsius)
    tm_mes       DOUBLE PRECISION,
    tm_max       DOUBLE PRECISION,
    tm_min       DOUBLE PRECISION,
    ta_max       DOUBLE PRECISION,
    ta_min       DOUBLE PRECISION,

    -- Precipitation (mm)
    p_mes        DOUBLE PRECISION,
    p_max        DOUBLE PRECISION,

    -- Wind
    w_med        DOUBLE PRECISION,        -- Mean wind speed (km/h)
    w_racha_spd  DOUBLE PRECISION,        -- Max gust speed (km/h)
    w_racha_dir  DOUBLE PRECISION,        -- Max gust direction (degrees)

    -- Humidity
    hr           DOUBLE PRECISION,        -- Relative humidity (%)

    -- Day counters
    nt_30        DOUBLE PRECISION,        -- Days with max temp >= 30C
    nt_00        DOUBLE PRECISION,        -- Days with min temp <= 0C

    -- Ensure no duplicate station-month combinations
    UNIQUE (indicativo, date_id)
);


-- ----------------------------------------------------------------------------
-- Fact: annual climatology summaries
-- ----------------------------------------------------------------------------
CREATE TABLE fact_climatology_annual (
    id           SERIAL PRIMARY KEY,
    indicativo   TEXT NOT NULL REFERENCES dim_station(indicativo),
    year         INTEGER NOT NULL,

    -- Temperature (Celsius)
    tm_mes       DOUBLE PRECISION,
    tm_max       DOUBLE PRECISION,
    tm_min       DOUBLE PRECISION,
    ta_max       DOUBLE PRECISION,
    ta_min       DOUBLE PRECISION,

    -- Precipitation (mm)
    p_mes        DOUBLE PRECISION,
    p_max        DOUBLE PRECISION,

    -- Wind
    w_med        DOUBLE PRECISION,
    w_racha_spd  DOUBLE PRECISION,
    w_racha_dir  DOUBLE PRECISION,

    -- Humidity
    hr           DOUBLE PRECISION,

    -- Day counters
    nt_30        DOUBLE PRECISION,
    nt_00        DOUBLE PRECISION,

    UNIQUE (indicativo, year)
);


-- ----------------------------------------------------------------------------
-- Indexes to speed up common queries (filtering by station or time)
-- ----------------------------------------------------------------------------
CREATE INDEX idx_fact_monthly_station ON fact_climatology_monthly(indicativo);
CREATE INDEX idx_fact_monthly_date    ON fact_climatology_monthly(date_id);
CREATE INDEX idx_fact_annual_station  ON fact_climatology_annual(indicativo);
CREATE INDEX idx_fact_annual_year     ON fact_climatology_annual(year);