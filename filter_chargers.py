import json
from shapely.geometry import shape, Point

def main():
    print("Loading CMA boundary...")
    with open("CMA.geojson", "r") as f:
        cma_data = json.load(f)

    # CMA geometry is a Polygon or MultiPolygon
    cma_geom = shape(cma_data["features"][0]["geometry"])

    print("Loading EV chargers...")
    with open("EV_Charger/tata_ev_chargers.geojson", "r") as f:
        chargers_data = json.load(f)

    print("Filtering chargers inside CMA...")
    cma_chargers = []
    for feature in chargers_data["features"]:
        coords = feature["geometry"]["coordinates"]
        point = Point(coords[0], coords[1])
        if cma_geom.contains(point):
            cma_chargers.append(feature)

    print(f"Filtered {len(cma_chargers)} EV chargers inside CMA boundary.")

    # Save to cma_ev_chargers.geojson
    output_data = {
        "type": "FeatureCollection",
        "features": cma_chargers
    }

    with open("cma_ev_chargers.geojson", "w") as f:
        json.dump(output_data, f)
    print("Saved filtered chargers to cma_ev_chargers.geojson.")

if __name__ == "__main__":
    main()
