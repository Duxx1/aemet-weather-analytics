# 05 · Exploratory Data Analysis — Climatology

## Context

This notebook performs an exploratory data analysis on the cleaned monthly climatology dataset produced by `clean_climatology.py`. The goal is to understand the climatic behaviour of the province of Badajoz across three dimensions — temperature, precipitation, and wind — and to identify patterns, anomalies, and inter-station differences that can inform the final Power BI dashboard.

**Position in the pipeline:**

```
[validate_raw_data] → [clean_climatology] → eda_climatology ← YOU ARE HERE
                                                    ↓
                                             Power BI dashboard
```

---

## Notebook

`notebooks/eda_climatology.ipynb`

### Dependencies

```bash
pip install pandas matplotlib seaborn pyarrow
```

### Input

`data/processed/climatology_monthly.parquet` — 4,766 monthly records across 24 stations.

---

## Station selection

The full dataset covers 24 stations, but their temporal coverage varies significantly. Stations with data only from 2021 or 2022 onwards cannot contribute to long-term trend analysis. The analysis focuses on five stations with the best historical coverage and continuous data through 2025:

| Station | First record | Last record | Records |
|---|---|---|---|
| 4452 | 2000-01 | 2025-12 | 312 |
| 4358X | 2003-01 | 2025-12 | 267 |
| 4468X | 2003-04 | 2025-12 | 263 |
| 4410X | 2000-01 | 2025-12 | 262 |
| 4244X | 2001-02 | 2025-12 | 234 |

---

## Data quality decisions

### Incomplete years

Years with fewer than 10 months of data are excluded from annual aggregations. Computing an annual mean from 1 or 2 months produces a heavily biased value that misrepresents the full year. For example, station `4244X` had only 1 month of data in 2007, which produced an apparent annual mean of ~8.5°C — impossible for Badajoz.

Applying the 10-month threshold removed 63 records, leaving 1,275 records in the working subset.

### Variables excluded from analysis

Fields with missingness above 70% were excluded from the main analysis because they are only present in records from approximately 2015 onwards and cannot support long-term comparisons:

- `inso`, `p_sol` (~80% missing)
- `q_min`, `q_max`, `q_med`, `q_mar` (~75% missing)
- `n_cub`, `n_des`, `n_nub` (~70% missing)
- `nv_*`, `n_tor`, `n_llu`, `n_nie` (>90% missing)

### Wind direction encoding

AEMET encodes `w_racha_dir` on a 1–36 scale (each unit = 10°) rather than in compass degrees. This was discovered during the EDA when wind rose plots showed all wind concentrated in a single sector. The conversion (`× 10`) was applied in `clean_climatology.py` so the field is already in degrees in the processed dataset.

---

## Analysis sections

### 1. Dataset overview

- **Missingness by column:** core temperature and precipitation variables have less than 3% missing values. Wind and humidity fields have ~10-12% missingness. Pressure, sunshine, and event counter fields exceed 70%.
- **Record availability heatmap:** visualizes which stations have data for each year, making coverage gaps immediately visible. Most stations begin in 2008; only five have pre-2008 records.

### 2. Temperature analysis

**Annual mean temperature trend**

The five stations move within the 16–20°C band. Station `4358X` is consistently the warmest from 2009 onwards. A mild upward trend is visible from approximately 2010, more pronounced in `4358X` and `4452`.

**Seasonal profile**

All stations follow an identical seasonal pattern: mean temperatures range from ~8°C in January to ~27°C in July-August. Inter-station differences are small (1–2°C in any given month), confirming the climatic homogeneity of the province.

**Absolute extremes**

Maximum absolute temperatures range between 28°C and 33°C depending on year and station. Minimum absolute temperatures are consistently between 3°C and 7°C. Year-to-year variability in extremes is high, driven by specific synoptic episodes rather than seasonal patterns.

### 3. Precipitation analysis

**Annual total precipitation**

High inter-annual variability is the defining characteristic: annual totals range from ~200mm to ~800mm depending on station and year. Wet years (2010, 2018, 2025) are synchronised across stations, indicating province-scale weather events rather than local phenomena.

**Seasonal profile**

A clearly Mediterranean pattern: summers are dry (July-August average ~3-5mm), with rainfall concentrated in autumn, winter, and spring. Station `4468X` shows an exceptionally high October mean (~100mm), approximately double the other stations, suggesting stronger exposure to DANA (cold drop) events.

**Dry months**

All stations average ~3–5 dry months per year (< 10mm). No clear trend of increasing or decreasing dry months over the study period.

**Maximum single-day precipitation**

Station `4358X` recorded an extreme event in 2015 (~100mm in a single day).

### 4. Wind analysis

**Mean wind speed**

Stations `4452` and `4468X` are the windiest (~10–12 km/h annual mean). Station `4358X` is the calmest (~6–7 km/h). Wind speed in `4358X` shows anomalously low values before 2009, likely due to sparse data coverage in that period.

**Seasonal profile**

Wind is strongest in spring (March–July) and weakest in autumn. This pattern is consistent with the pressure gradient dynamics of the Iberian Peninsula, where Atlantic fronts are more active in spring.

**Wind rose**

Both analyzed stations (`4452` and `4244X`) show dominant wind gust directions from the north-northwest (300°), west (270°) and south-southwest (200–220°), reflecting the influence of Atlantic weather systems and the topography of the Guadiana basin.

**Independence from other variables**

Wind speed shows near-zero correlation with both temperature (r = 0.07) and precipitation (r = 0.14), confirming it is driven by independent synoptic factors.

---

## Correlation matrix highlights

| Variable pair | r | Interpretation |
|---|---|---|
| `tm_mes` ↔ `tm_max` | 0.99 | All temperature variables move together |
| `tm_mes` ↔ `hr` | -0.86 | Hotter months have lower relative humidity |
| `tm_mes` ↔ `nt_30` | 0.92 | Monthly mean temperature predicts hot days well |
| `p_mes` ↔ `p_max` | 0.83 | Wetter months also produce more intense daily events |
| `w_med` ↔ `tm_mes` | 0.07 | Wind is independent of temperature |
| `tm_min` ↔ `nt_00` | -0.56 | Colder monthly minima mean more frost days |

---

## Conclusions

### Temperature
- Homogeneous thermal regime across the province, consistent with a Mediterranean-continental climate.
- `4358X` is the warmest station and `4468X` the coolest, suggesting differences in altitude or local exposure.
- A mild warming trend is visible from 2010 onwards, particularly in `4358X` and `4452`.
- Mean monthly temperature is a strong predictor of hot days (`nt_30`, r = 0.92) and negatively correlated with relative humidity (r = -0.86).

### Precipitation
- High inter-annual variability (200–800mm/year) with a clearly Mediterranean seasonal distribution.
- `4468X` shows exceptional October rainfall, likely driven by DANA events.
- `4358X` is the driest station overall; `4244X` and `4468X` record the most intense single-day episodes.
- Wetter months consistently produce more intense daily events (r = 0.83).

### Wind
- `4452` and `4468X` are the windiest stations; `4358X` the calmest.
- Dominant gust direction is west-northwest to south-southwest, driven by Atlantic systems.
- Wind is statistically independent of temperature and precipitation.
