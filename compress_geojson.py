import json
import gzip
import os

use_mapping = {
    'Residential (Low Density)': 'RL',
    'Residential / Independent House': 'RI',
    'Apartments / Mixed-Use': 'AM',
    'Apartments (Medium Rise)': 'AMM',
    'Apartments (High Rise)': 'AMH',
    'Commercial / Retail': 'CR',
    'Commercial / Office / Retail': 'COR',
    'Commercial / Office': 'CO',
    'Commercial Office Tower / Corporate Hub': 'COT',
    'Industrial / Warehouse': 'IW',
    'Institutional / Public Building': 'IP'
}

input_path = "/Volumes/Sandisk SSD/Google_building/cma_buildings_3d.geojson"
output_path = "/Volumes/Sandisk SSD/Google_building/cma_buildings_3d.geojson"
temp_output_path = "/Volumes/Sandisk SSD/Google_building/cma_buildings_3d_temp.geojson"

print("Starting GeoJSON compression...")
print("Reading source file...")

with open(input_path, 'r') as f:
    data = json.load(f)

print(f"Loaded {len(data['features'])} features.")
print("Processing features...")

def round_coords(coords):
    if isinstance(coords[0], list):
        return [round_coords(c) for c in coords]
    else:
        # Round coordinates to 6 decimal places (approx. 10cm accuracy)
        return [round(coords[0], 6), round(coords[1], 6)]

processed_features = []
for idx, feature in enumerate(data['features']):
    props = feature.get('properties', {})
    geom = feature.get('geometry', {})
    
    # 1. Compress properties
    h = props.get('height', 0)
    a = props.get('area', 0)
    est_use = props.get('estimated_use', 'Unknown')
    
    compact_props = {
        'h': round(h, 1),
        'a': int(round(a)),
        'u': use_mapping.get(est_use, 'UNK')
    }
    
    # 2. Compress geometry coordinates
    coords = geom.get('coordinates', [])
    compact_geom = {
        'type': geom.get('type'),
        'coordinates': round_coords(coords)
    }
    
    compact_feature = {
        'type': 'Feature',
        'properties': compact_props,
        'geometry': compact_geom
    }
    
    processed_features.append(compact_feature)
    
    if (idx + 1) % 100000 == 0:
        print(f"Processed {idx + 1} features...")

compact_data = {
    'type': 'FeatureCollection',
    'features': processed_features
}

print("Writing compact GeoJSON to temp file (minimized JSON)...")
with open(temp_output_path, 'w', encoding='utf-8') as f:
    # Use separators to remove all unnecessary whitespace
    json.dump(compact_data, f, separators=(',', ':'))

# Replace original file
if os.path.exists(input_path):
    os.remove(input_path)
os.rename(temp_output_path, output_path)

print(f"Compact GeoJSON size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

# Now gzip the compact file
gz_output_path = output_path + ".gz"
print(f"Gzipping compact file to {gz_output_path}...")
with open(output_path, 'rb') as f_in:
    with gzip.open(gz_output_path, 'wb', compresslevel=9) as f_out:
        f_out.writelines(f_in)

print(f"Compressed GZ size: {os.path.getsize(gz_output_path) / (1024*1024):.2f} MB")
print("Optimization completed successfully!")
