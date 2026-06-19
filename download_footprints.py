import urllib.request
import gzip
import csv
import json
import sys
import os
import ssl

# Bypass SSL verification if needed (common on macOS Python)
ssl._create_default_https_context = ssl._create_unverified_context

# Target footprint URL for S2 cell 3a5 (covers Chennai area)
FOOTPRINT_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/3a5_buildings.csv.gz"
CMA_GEOJSON_PATH = "CMA.geojson"
OUTPUT_PATH = "cma_buildings_footprints.geojson"

# Ensure dependencies are available
try:
    from shapely.geometry import shape, Point
    from shapely.wkt import loads as load_wkt
except ImportError:
    print("Error: The 'shapely' library is required to run this script.")
    print("Please install it using: pip install shapely")
    sys.exit(1)

try:
    from tqdm import tqdm
    has_tqdm = True
except ImportError:
    has_tqdm = False
    print("Note: 'tqdm' library not installed. Running without progress bar.")

def main():
    # 1. Load the CMA boundary
    if not os.path.exists(CMA_GEOJSON_PATH):
        print(f"Error: Boundary file '{CMA_GEOJSON_PATH}' not found in the current directory.")
        sys.exit(1)
        
    print(f"Loading boundary from {CMA_GEOJSON_PATH}...")
    with open(CMA_GEOJSON_PATH, 'r') as f:
        cma_data = json.load(f)
        
    cma_geom = shape(cma_data["features"][0]["geometry"])
    
    # 2. Calculate Bounding Box of the CMA boundary
    min_lon, min_lat, max_lon, max_lat = cma_geom.bounds
    print(f"CMA Bounding Box: [{min_lon:.5f}, {min_lat:.5f}, {max_lon:.5f}, {max_lat:.5f}]")
    
    # 3. Stream and filter the 1.07 GB gzipped footprint CSV file
    print(f"Streaming data from Google GCS: {FOOTPRINT_URL} ...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(FOOTPRINT_URL, headers=headers)
    
    features = []
    total_processed = 0
    total_saved = 0
    
    try:
        with urllib.request.urlopen(req) as response:
            # We wrap the response stream with gzip decompressor
            with gzip.open(response, mode='rt', encoding='utf-8') as gz_file:
                # Read CSV
                reader = csv.reader(gz_file)
                # Read header
                header = next(reader)
                
                # Check columns structure
                lat_idx = header.index('latitude')
                lon_idx = header.index('longitude')
                area_idx = header.index('area_in_meters')
                conf_idx = header.index('confidence')
                wkt_idx = header.index('geometry')
                plus_idx = header.index('full_plus_code')
                
                print("Starting stream processing. Filtering by bounding box first...")
                
                # Use tqdm if available, otherwise fallback
                if has_tqdm:
                    pbar = tqdm(unit='lines', desc='Processing buildings')
                else:
                    pbar = None
                    
                for row in reader:
                    total_processed += 1
                    if pbar is not None:
                        pbar.update(1)
                    elif total_processed % 100000 == 0:
                        print(f"Processed {total_processed} lines, saved {total_saved} buildings so far...")
                        
                    try:
                        lat = float(row[lat_idx])
                        lon = float(row[lon_idx])
                    except ValueError:
                        continue
                        
                    # numerical bounding box check (takes microseconds)
                    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                        continue
                        
                    # Centroid point check
                    pt = Point(lon, lat)
                    if not cma_geom.contains(pt):
                        continue
                        
                    # Footprint exact intersection check
                    wkt_geom = row[wkt_idx]
                    try:
                        building_shape = load_wkt(wkt_geom)
                    except Exception:
                        continue
                        
                    # Create GeoJSON feature
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "area": float(row[area_idx]),
                            "confidence": float(row[conf_idx]),
                            "plus_code": row[plus_idx],
                            "centroid_lat": lat,
                            "centroid_lon": lon
                        },
                        "geometry": building_shape.__geo_interface__
                    }
                    features.append(feature)
                    total_saved += 1
                    
                if pbar is not None:
                    pbar.close()
                    
    except Exception as e:
        print(f"\nError streaming/processing data: {e}")
        sys.exit(1)
        
    print(f"\nFinished stream processing!")
    print(f"Total rows read from GCS: {total_processed}")
    print(f"Total buildings inside CMA: {total_saved}")
    
    # 4. Save to GeoJSON
    print(f"Saving filtered buildings to {OUTPUT_PATH}...")
    output_geojson = {
        "type": "FeatureCollection",
        "name": "CMA_Buildings_Footprints",
        "features": features
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output_geojson, f)
        
    print(f"Successfully saved {total_saved} building footprints to {OUTPUT_PATH}!")

if __name__ == "__main__":
    main()
