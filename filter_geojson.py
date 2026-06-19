import json
import os
import sys

INPUT_PATH = "cma_buildings_3d.geojson"
# We overwrite the input file directly so index.html loads it without changes
OUTPUT_PATH = "cma_buildings_3d.geojson"

def main():
    if not os.path.exists(INPUT_PATH):
        print(f"Error: Input file '{INPUT_PATH}' not found.")
        sys.exit(1)
        
    # Read the full file. Since it is ~1.47 GB, this will load it.
    print(f"Loading building data from {INPUT_PATH}...")
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)
        
    features = data.get("features", [])
    total = len(features)
    print(f"Original count: {total:,} buildings.")
    
    # Filtering criteria:
    # 1. Keep ALL buildings with height >= 6.0 meters (multi-story buildings: 2+ floors)
    # 2. Keep single-story buildings (height < 6.0m) only if:
    #    - area >= 200 m2 AND confidence >= 0.85
    
    filtered_features = []
    
    for f in features:
        props = f.get("properties", {})
        h = props.get("height", 3.0)
        area = props.get("area", 0)
        conf = props.get("confidence", 0.0)
        
        # Rule:
        if h >= 6.0:
            filtered_features.append(f)
        elif area >= 200 and conf >= 0.85:
            filtered_features.append(f)
            
    filtered_count = len(filtered_features)
    pct = (filtered_count / total) * 100
    print(f"Filtered count: {filtered_count:,} buildings ({pct:.1f}% of total).")
    
    # Save the filtered dataset (overwriting cma_buildings_3d.geojson)
    print(f"Saving filtered buildings back to {OUTPUT_PATH}...")
    data["features"] = filtered_features
    
    # We save to a temp file first, then rename it, to prevent data corruption if interrupted
    tmp_path = OUTPUT_PATH + ".tmp"
    with open(tmp_path, 'w') as f:
        json.dump(data, f)
        
    if os.path.exists(OUTPUT_PATH):
        os.remove(OUTPUT_PATH)
    os.rename(tmp_path, OUTPUT_PATH)
    
    # Also clean up the footprints file if it exists, to save another 1.42 GB of disk space!
    footprints_file = "cma_buildings_footprints.geojson"
    if os.path.exists(footprints_file):
        os.remove(footprints_file)
        print(f"Deleted intermediate footprints file '{footprints_file}' to free up disk space.")
        
    # Also delete the temporary filtered file from earlier if it exists
    old_filtered = "cma_buildings_3d_filtered.geojson"
    if os.path.exists(old_filtered):
        os.remove(old_filtered)
        print(f"Deleted intermediate file '{old_filtered}'.")
        
    print(f"Successfully saved final optimized dataset of {filtered_count:,} buildings to {OUTPUT_PATH}!")

if __name__ == "__main__":
    main()
