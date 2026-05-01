# Download Climatology Data (AEMET)

## 1. Objective

This step retrieves monthly climatology data for a set of weather stations in Badajoz using the AEMET OpenData API.

Due to API limitations, data must be downloaded in chunks and handled carefully to avoid rate limiting.

---

## 2. Input Data

The script expects a list of station identifiers (`indicativos`) stored in: `data/raw/badajoz_stations_indicativos.json`


Each entry represents a weather station.

---

## 3. Key API Constraints

The AEMET API imposes several important limitations:

- Maximum of **36 months per request** → requires splitting into 3-year windows
- Requests are **rate-limited** → too many requests trigger HTTP 429 errors
- Data retrieval is a **two-step process**:
  1. Authenticated request (returns a temporary URL)
  2. Second request to download the actual data

---

## 4. Implementation Overview

The script `download_climatology.py` handles:

### Data Retrieval Strategy

- Iterates over each station (`indicativo`)
- Splits the time range (2000–2025) into 3-year windows
- Downloads each chunk independently

### Rate Limiting Protection

To avoid being blocked by the API:

- A **global request counter** is used
- After **50 requests**, the script pauses for **65 seconds**
- An additional **3-second delay between requests** is applied

This combination significantly reduces HTTP 429 errors.

### Two-Step API Call

Each dataset is retrieved using:

1. Authenticated request with API key → returns `"datos"` URL
2. Direct request to that URL → returns JSON data

Only the first request requires authentication.

---

## 5. Output

Downloaded data is stored as JSON files in: `data/raw/climatology/monthly/`

Each file follows this naming convention: `{indicativo}{start_year}{end_year}.json`

Example: `4244X_2000_2002.json`

---

## 6. Error Handling

- Failed requests are logged and stored in a list
- Common issues include:
  - HTTP 429 → Too many requests
  - HTTP 500 → Temporary server errors
  - Missing `"datos"` field in API response

These failures can be retried later if needed.

---

## 7. Notes on Data Quality

- Some months may be missing or partially populated
- Entries like `"fecha": "YYYY-13"` correspond to **annual summaries**
- Raw values often include embedded metadata (e.g. `"23.4(13)"`)

Data cleaning and normalization are handled in later steps.

