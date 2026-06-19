import json
import os
import sys

GEOJSON_PATH = "cma_buildings_3d.geojson"

def classify_building(height, area):
    # Estimate floors (default floor height is 3.5m)
    floors = max(1, round(height / 3.5))
    
    if floors == 1:
        if area < 150:
            return "Residential (Low Density)"
        elif area < 600:
            return "Commercial / Retail"
        else:
            return "Industrial / Warehouse"
            
    elif floors <= 3: # 2-3 floors
        if area < 250:
            return "Residential / Independent House"
        elif area < 600:
            return "Apartments / Mixed-Use"
        else:
            return "Commercial / Office / Retail"
            
    elif floors <= 6: # 4-6 floors (Medium Rise)
        if area < 500:
            return "Apartments (Medium Rise)"
        elif area < 1200:
            return "Commercial / Office"
        else:
            return "Institutional / Public Building"
            
    else: # 7+ floors (High Rise / Skyline)
        if area < 800:
            return "Apartments (High Rise)"
        else:
            return "Commercial Office Tower / Corporate Hub"

def main():
    if not os.path.exists(GEOJSON_PATH):
        print(f"Error: {GEOJSON_PATH} not found.")
        sys.exit(1)
        
    print(f"Loading 3D buildings from {GEOJSON_PATH}...")
    with open(GEOJSON_PATH, 'r') as f:
        data = json.load(f)
        
    features = data.get("features", [])
    print(f"Classifying {len(features):,} buildings...")
    
    use_counts = {}
    
    for f in features:
        props = f.get("properties", {})
        height = props.get("height", 3.0)
        area = props.get("area", 0)
        
        b_use = classify_building(height, area)
        props["estimated_use"] = b_use
        
        use_counts[b_use] = use_counts.get(b_use, 0) + 1
        
    print("\n--- Classification Stats ---")
    for b_use, count in sorted(use_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{b_use}: {count:,} buildings ({count/len(features)*100:.1f}%)")
        
    print(f"\nSaving classified building data back to {GEOJSON_PATH}...")
    with open(GEOJSON_PATH, 'w') as f:
        json.dump(data, f)
        
    print("Classification completed successfully!")

if __name__ == "__main__":
    main()
