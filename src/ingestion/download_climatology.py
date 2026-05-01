from dotenv import load_dotenv
import os
import requests
import json
import time

load_dotenv()
API_KEY = os.getenv("AEMET_API_KEY")

HEADERS = {"api_key": API_KEY}

INPUT_PATH = "data/raw/badajoz_stations_indicativos.json"
OUTPUT_DIR = "data/raw/climatology/monthly/"

BASE_URL = "https://opendata.aemet.es/opendata/api/valores/climatologicos/mensualesanuales/datos"

# Rate limit config
REQUEST_LIMIT = 50
SLEEP_TIME = 65

# Global counter to enforce API rate limits across requests
request_count = 0

def rate_limited_get(url: str, use_api_key: bool = True) -> requests.Response:
    global request_count

    # Hard cap to avoid hitting AEMET request limits
    if request_count >= REQUEST_LIMIT:
        print(f"\nReached {REQUEST_LIMIT} requests. Sleeping {SLEEP_TIME}s...\n")
        time.sleep(SLEEP_TIME)
        request_count = 0

    if use_api_key:
        response = requests.get(url, headers={"api_key": API_KEY})
    else:
        response = requests.get(url)

    request_count += 1
    # Additional delay between requests to reduce risk of HTTP 429
    time.sleep(3)

    return response

def load_indicativos() -> list[str]:
    with open(INPUT_PATH, "r") as f:
        return json.load(f)

# Authentication only in the first call
def call_aemet(url: str) -> dict:
    response = rate_limited_get(url, use_api_key=True) # the first call requires the api key
    response.raise_for_status()
    return response.json()

# AEMET API requires a two-step request:
# 1. Authenticated call → returns a temporary URL in "datos"
# 2. Direct call to that URL → returns actual data
def fetch_data(url: str) -> list[dict]:
    data = call_aemet(url)

    # Ensure API returned the expected structure
    if "datos" not in data:
        print("API response:", data)
        raise ValueError("No 'datos' field")

    data_url = data["datos"]

    response = rate_limited_get(data_url, use_api_key=False) # the second call only requires the url
    response.raise_for_status()

    return response.json()

# AEMET API limitation:
# Maximum range per request is 36 months -> requires chunking in 3-year windows
def build_url(indicativo: str, start_year: int, end_year: int) -> str:
    return f"{BASE_URL}/anioini/{start_year}/aniofin/{end_year}/estacion/{indicativo}"


def save_json(data: list[dict], indicativo_and_years: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{indicativo_and_years}.json")

    with open(path, "w") as f:
        json.dump(data, f)


def main() -> None:

    indicativos = load_indicativos()
    # Store failed requests for later inspection or retry
    failed = []

    # Iterate over each station and retrieve data in 3-year windows
    for ind in indicativos:

        # for each indicativo, it is needed to retrieve data in windows of 3 years because of the API
        for year in range(2000, 2025, 3):
            start = year
            end = min(year + 2, 2025)

            try:
                print(f"{ind} | {start}-{end}")

                url = build_url(ind, start, end)
                data = fetch_data(url)

                save_json(data, f"{ind}_{start}_{end}")

            except Exception as e:
                failed.append(f"{ind} | {start}-{end}")
                print(f"Skipping {ind} {start}-{end}: {e}")
            
    print("Failed stations:", failed)


if __name__ == "__main__":
    main()
