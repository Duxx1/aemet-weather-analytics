# AEMET Variables Reference

This document describes all variables present in the cleaned climatology datasets
(`climatology_monthly.csv` and `climatology_annual.csv`). It serves as a reference
for understanding what each field represents before performing any analysis.

---

## Identifiers and date fields

| Variable | Description |
|---|---|
| `indicativo` | AEMET station identifier. Unique code assigned to each weather station. |
| `fecha` | Date of the record. Format `YYYY-MM` for monthly records, `YYYY-13` for annual summaries. |
| `year` | Calendar year extracted from `fecha`. |
| `month` | Calendar month extracted from `fecha` (monthly dataset only). |

---

## Temperature (°C)

| Variable | Description |
|---|---|
| `tm_mes` | Mean monthly temperature. Average of all daily mean temperatures in the month. |
| `tm_max` | Mean of daily maximum temperatures. Average of each day's highest temperature. |
| `tm_min` | Mean of daily minimum temperatures. Average of each day's lowest temperature. |
| `ta_max` | Absolute maximum temperature recorded in the month. The single highest reading. |
| `ta_min` | Absolute minimum temperature recorded in the month. The single lowest reading. |
| `ts_min` | Minimum temperature recorded at ground level (grass surface), which is typically lower than air temperature. |
| `ti_max` | Maximum temperature recorded inside a radiation shelter at a low height. Used as a proxy for soil surface warming. |

---

## Precipitation (mm)

| Variable | Description |
|---|---|
| `p_mes` | Total monthly precipitation. Sum of all rainfall in the month. |
| `p_max` | Maximum precipitation recorded in a single day within the month. |

---

## Precipitation day counters

These count the number of days in the month that meet a specific precipitation threshold.

| Variable | Threshold | Description |
|---|---|---|
| `np_001` | ≥ 0.1 mm | Days with any measurable precipitation. |
| `np_010` | ≥ 1.0 mm | Days with light or more precipitation. |
| `np_100` | ≥ 10.0 mm | Days with moderate or heavy precipitation. |
| `np_300` | ≥ 30.0 mm | Days with very heavy precipitation. |

---

## Wind

| Variable | Description |
|---|---|
| `w_med` | Mean daily wind speed (km/h). Average across all hours of the month. |
| `w_rec` | Total wind run (km). Cumulative distance travelled by wind during the month. |
| `w_racha_spd` | Speed of the maximum wind gust recorded in the month (km/h). Derived from AEMET's `w_racha` field. |
| `w_racha_dir` | Direction from which the maximum wind gust came, in compass degrees (0–360). AEMET stores this internally as a 1–36 scale (each unit = 10°), which is converted to degrees during cleaning. |
| `nw_55` | Number of days with wind gusts ≥ 55 km/h. |
| `nw_91` | Number of days with wind gusts ≥ 91 km/h (storm-force winds). |

---

## Atmospheric pressure (hPa)

These fields are only available for stations equipped with a barometer. Missingness is high (~75%) because many stations in the dataset do not record pressure.

| Variable | Description |
|---|---|
| `q_med` | Mean sea-level pressure for the month. |
| `q_max` | Maximum sea-level pressure recorded in the month. |
| `q_min` | Minimum sea-level pressure recorded in the month. |
| `q_mar` | Mean station-level pressure (not reduced to sea level). |

---

## Humidity and evaporation

| Variable | Description |
|---|---|
| `hr` | Mean relative humidity (%). Average across all daily readings. |
| `e` | Total monthly evaporation (mm). Measured with a Piché evaporimeter or equivalent. |

---

## Sunshine and solar radiation

These fields have high missingness (~80%) as they require specific instrumentation not available at all stations.

| Variable | Description |
|---|---|
| `inso` | Mean daily sunshine hours. Average number of hours per day with direct sunlight. |
| `p_sol` | Sunshine percentage. Ratio of actual sunshine hours to maximum possible sunshine hours (%), expressed as a monthly mean. |

---

## Temperature extreme day counters

| Variable | Description |
|---|---|
| `nt_30` | Number of days with maximum temperature ≥ 30 °C (hot days). |
| `nt_00` | Number of days with minimum temperature ≤ 0 °C (frost days). |

---

## Cloud cover and visibility

These fields are only present in records from approximately 2015 onwards. Missingness exceeds 70%.

| Variable | Description |
|---|---|
| `n_cub` | Number of days with overcast sky (cloud cover 7–8 oktas). |
| `n_des` | Number of days with clear sky (cloud cover 0–2 oktas). |
| `n_nub` | Number of days with partly cloudy sky (cloud cover 3–6 oktas). |
| `nv_0050` | Number of days with visibility below 50 m (dense fog). |
| `nv_0100` | Number of days with visibility below 100 m. |
| `nv_1000` | Number of days with visibility below 1,000 m (fog). |

---

## Weather event counters

These fields are only present in records from approximately 2015 onwards. Missingness exceeds 90%.

| Variable | Description |
|---|---|
| `n_llu` | Number of days with rainfall. |
| `n_nie` | Number of days with snowfall. |
| `n_tor` | Number of days with thunderstorms. |
| `n_gra` | Number of days with hail. |
| `n_fog` | Number of days with fog. |

---

## Notes on missing values

Missing values (`NaN`) appear for two distinct reasons:

1. **Schema evolution:** AEMET expanded its published variables over time. Fields like `inso`, `n_llu`, `n_tor`, `n_cub`, `nv_*` were added later and are absent in older records. This is the main source of missingness in this dataset.

2. **Station equipment:** Some variables (pressure, sunshine) require specific instruments not present at every station. These will be missing for the entire history of stations without that equipment.

Missing values in the core temperature and precipitation variables (`tm_mes`, `ta_max`, `p_mes`, etc.) are rare (~2–3%) and correspond to months where AEMET did not publish data for that station.