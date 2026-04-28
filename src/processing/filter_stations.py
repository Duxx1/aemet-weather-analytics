import json

INPUT_PATH = "data/raw/stations.json"
OUTPUT_PATH = "data/raw/badajoz_stations.json"

def load_stations():
    with open(INPUT_PATH, "r") as f:
        return json.load(f)

def get_stations_by_provincia(stations : list, provincia: str = "BADAJOZ"):
    filtered = list()

    for station in stations:
        if station["provincia"] == provincia:
            filtered.append(station)
    
    return filtered

def extract_indicativos(stations: list):
    return {s["indicativo"] for s in stations}

def save_json(data, path: str):
    with open(path, "w") as f:
            json.dump(data, f, indent=4)

if __name__ == "__main__":
    stations = load_stations()

    badajoz_stations = get_stations_by_provincia(stations, "BADAJOZ")
    indicativos = extract_indicativos(badajoz_stations)

    save_json(badajoz_stations, OUTPUT_PATH)
    save_json(list(indicativos), "data/raw/badajoz_stations_indicativos.json")

    print(f"Estaciones BADAJOZ: {len(badajoz_stations)}")
    print(f"Indicativos unicos: {len(indicativos)}")


