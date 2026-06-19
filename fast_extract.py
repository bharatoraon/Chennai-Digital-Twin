import subprocess
import json
import os
import sys
import time

CMA_GEOJSON_PATH = "CMA.geojson"
FILTERED_CSV_PATH = "cma_filtered.csv"
OUTPUT_PATH = "cma_buildings_footprints.geojson"
FOOTPRINT_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/3a5_buildings.csv.gz"

# Bounding box for Chennai CMA
MIN_LON, MIN_LAT = 79.54937536093246, 12.468813479275637
MAX_LON, MAX_LAT = 80.34881798479452, 13.562842581083572

# Ensure shapely is available
try:
    from shapely.geometry import shape, Point
    from shapely.wkt import loads as load_wkt
    from shapely.prepared import prep
except ImportError:
    print("Error: The 'shapely' library is required to run this script.")
    print("Please install it using: pip install shapely")
    sys.exit(1)

try:
    from tqdm import tqdm
    has_tqdm = True
except ImportError:
    has_tqdm = False

def main():
    start_time = time.time()
    
    # 1. Load the CMA boundary
    if not os.path.exists(CMA_GEOJSON_PATH):
        print(f"Error: Boundary file '{CMA_GEOJSON_PATH}' not found.")
        sys.exit(1)
        
    print(f"Loading boundary from {CMA_GEOJSON_PATH}...")
    with open(CMA_GEOJSON_PATH, 'r') as f:
        cma_data = json.load(f)
    cma_geom = shape(cma_data["features"][0]["geometry"])
    
    # Optimize contains queries by preparing the geometry (creates an R-tree index)
    print("Preparing boundary geometry for high-speed spatial queries...")
    prepared_cma = prep(cma_geom)
    
    # 2. Run high-speed streaming pipeline to create cma_filtered.csv (if not already done)
    print("\n--- STAGE 1: High-Speed Streaming Filter ---")
    if os.path.exists(FILTERED_CSV_PATH) and os.path.getsize(FILTERED_CSV_PATH) > 0:
        print(f"Temporary file '{FILTERED_CSV_PATH}' already exists. Skipping download and reuse...")
    else:
        print(f"Downloading and filtering S2 tile 3a5 on-the-fly...")
        print(f"BBox: [{MIN_LON:.5f}, {MIN_LAT:.5f}, {MAX_LON:.5f}, {MAX_LAT:.5f}]")
        
        # Construct shell command
        cmd = (
            f"curl -L -s '{FOOTPRINT_URL}' | "
            f"gunzip -c | "
            f"awk -F, 'NR==1 || ($1 >= {MIN_LAT} && $1 <= {MAX_LAT} && $2 >= {MIN_LON} && $2 <= {MAX_LON})' "
            f"> {FILTERED_CSV_PATH}"
        )
        
        print(f"Running command: {cmd}")
        try:
            process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print("Streaming filter completed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error running streaming pipeline: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            sys.exit(1)
            
        print(f"Filtered CSV saved to '{FILTERED_CSV_PATH}' (Size: {os.path.getsize(FILTERED_CSV_PATH) / (1024*1024):.2f} MB)")
    
    # 3. Precise Shape Intersection
    print("\n--- STAGE 2: Precise Spatial Intersection ---")
    print(f"Reading filtered CSV and verifying overlap with prepared CMA polygon...")
    
    features = []
    total_processed = 0
    total_saved = 0
    
    try:
        import csv
        
        # Determine total rows if tqdm is available to show progress
        if has_tqdm:
            # Quick count of lines in filtered csv
            print("Counting lines in filtered CSV to initialize progress bar...")
            with open(FILTERED_CSV_PATH, 'rb') as f:
                num_lines = sum(1 for _ in f) - 1
            print(f"Found {num_lines:,} candidate buildings in bounding box.")
            pbar = tqdm(total=num_lines, desc="Verifying overlap")
        else:
            pbar = None
            
        with open(FILTERED_CSV_PATH, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Identify column indices
            lat_idx = header.index('latitude')
            lon_idx = header.index('longitude')
            area_idx = header.index('area_in_meters')
            conf_idx = header.index('confidence')
            wkt_idx = header.index('geometry')
            plus_idx = header.index('full_plus_code')
            
            for row in reader:
                total_processed += 1
                if pbar is not None:
                    pbar.update(1)
                elif total_processed % 100000 == 0:
                    print(f"Checked {total_processed:,} candidates, saved {total_saved:,} buildings...")
                    
                try:
                    lat = float(row[lat_idx])
                    lon = float(row[lon_idx])
                except ValueError:
                    continue
                
                # High-speed centroid check using prepared geometry
                pt = Point(lon, lat)
                if not prepared_cma.contains(pt):
                    continue
                    
                # Load exact polygon geometry
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
        print(f"Error during spatial intersection: {e}")
        sys.exit(1)
        
    print(f"Rows checked: {total_processed:,}")
    print(f"Buildings inside exact CMA boundary: {total_saved:,}")
    
    # 4. Save to GeoJSON
    print(f"Saving final footprints to {OUTPUT_PATH}...")
    output_geojson = {
        "type": "FeatureCollection",
        "name": "CMA_Buildings_Footprints",
        "features": features
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output_geojson, f)
        
    # Clean up temp file
    if os.path.exists(FILTERED_CSV_PATH):
        os.remove(FILTERED_CSV_PATH)
        print(f"Temporary file '{FILTERED_CSV_PATH}' deleted.")
        
    elapsed = time.time() - start_time
    print(f"\n--- SUCCESS ---")
    print(f"Extracted {total_saved:,} building footprints in {elapsed:.1f} seconds!")
    print(f"Output saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
