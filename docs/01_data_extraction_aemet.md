# AEMET Data Download – Setup & First Extraction

## 1. API Key Setup

To interact with the AEMET OpenData API:

1. Register at: https://opendata.aemet.es
2. Generate your personal API key
3. Create a `.env` file in the root of the project:

```
AEMET_API_KEY=your_api_key_here
```

The project loads this key automatically at runtime.

---

## 2. Purpose of This Step

This stage focuses on:

* Connecting to the AEMET API
* Retrieving the full list of weather stations
* Storing the data in raw format for later use

This is the **entry point of the data pipeline**.

---

## 3. Extraction Process (High-Level)

The extraction follows these steps:

1. Authentication using the API key
2. Send a request to the AEMET endpoint for station inventory
3. Receive a response containing a secondary URL
4. Perform a second request to download the actual data
5. Store the response locally as a JSON file

Important considerations:

* The API does not return data directly (two-step process)
* A small delay between requests is required to avoid rate limiting
* Data is stored without transformation (raw ingestion)

---

## 4. Output

After running the script, the following file is generated:

```
data/raw/stations.json
```

This dataset includes:

* Station identifiers (`indicativo`)
* Geographic information
* Metadata needed for downstream data collection

---

## 5. Notes & Limitations

* No data validation is performed at this stage
* API responses may occasionally fail
* Rate limiting is only partially handled
* Data may contain inconsistencies that will be addressed later

