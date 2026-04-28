from dotenv import load_dotenv
import os
import requests
import json
import time

load_dotenv()
API_KEY = os.getenv("AEMET_API_KEY")

HEADERS = {"api_key": API_KEY}

def call_aemet(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def fetch_data(url):
    data = call_aemet(url)
    data_url = data["datos"]
    time.sleep(1)
    return requests.get(data_url).json()

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f)

def get_stations():
    url = "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones"
    return fetch_data(url)

if __name__ == "__main__":
    stations = get_stations()
    save_json(stations, "data/raw/stations.json")