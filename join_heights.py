import json
import os
import sys

# Default paths
FOOTPRINTS_PATH = "cma_buildings_footprints.geojson"
HEIGHT_RASTER_PATH = "cma_building_height_2023.tif"
OUTPUT_PATH = "cma_buildings_3d.geojson"

# Ensure dependencies are available
try:
    import rasterio
except ImportError:
    print("Error: The 'rasterio' library is required to run this script.")
    print("Please install it using: pip install rasterio")
    sys.exit(1)

try:
    from tqdm import tqdm
    has_tqdm = True
except ImportError:
    has_tqdm = False

def main():
    # Check if files exist
    if not os.path.exists(FOOTPRINTS_PATH):
        print(f"Error: Footprint file '{FOOTPRINTS_PATH}' not found.")
        print("Please run 'download_footprints.py' first.")
        sys.exit(1)
        
    # Ask user or search for the height raster
    raster_file = HEIGHT_RASTER_PATH
    if not os.path.exists(raster_file):
        # Look for any tif file in the directory
        tifs = [f for f in os.listdir('.') if f.endswith('.tif') or f.endswith('.tiff')]
        if tifs:
            raster_file = tifs[0]
            print(f"Warning: Default raster '{HEIGHT_RASTER_PATH}' not found. Using '{raster_file}' instead.")
        else:
            print(f"Error: Building height GeoTIFF raster file (e.g., '{HEIGHT_RASTER_PATH}') not found.")
            print("Please make sure you have downloaded the GEE exported GeoTIFF files and placed them in this directory.")
            sys.exit(1)

    print(f"Loading building footprints from {FOOTPRINTS_PATH}...")
    with open(FOOTPRINTS_PATH, 'r') as f:
        footprints_data = json.load(f)
        
    features = footprints_data.get("features", [])
    num_buildings = len(features)
    print(f"Loaded {num_buildings} building footprints.")

    print(f"Opening building height GeoTIFF raster: {raster_file}...")
    try:
        with rasterio.open(raster_file) as src:
            print(f"Raster Dimensions: {src.width} x {src.height}")
            print(f"Raster CRS: {src.crs}")
            print(f"Raster Bounds: {src.bounds}")
            
            import numpy as np
            from rasterio.transform import rowcol

            # Read the raster band
            print("Reading raster band into memory...")
            band1 = src.read(1)
            height_dim, width_dim = band1.shape
            print(f"Raster loaded. Shape: {band1.shape}")

            print("Extracting footprint coordinates...")
            lons = []
            lats = []
            for feat in features:
                props = feat.get("properties", {})
                lons.append(props.get("centroid_lon"))
                lats.append(props.get("centroid_lat"))

            print("Calculating pixel indices for all centroids...")
            rows, cols = rowcol(src.transform, lons, lats)
            rows = np.array(rows)
            cols = np.array(cols)

            print("Sampling height values from raster array...")
            valid_mask = (rows >= 0) & (rows < height_dim) & (cols >= 0) & (cols < width_dim)
            
            sampled_heights = np.full(len(features), 3.0, dtype=np.float32)
            sampled_heights[valid_mask] = band1[rows[valid_mask], cols[valid_mask]]

            # Clean NaNs and invalid heights
            invalid_mask = (sampled_heights != sampled_heights) | (sampled_heights < 0) | (sampled_heights > 200)
            sampled_heights[invalid_mask] = 3.0

            print("Updating building features with heights...")
            count_valid = int(np.sum(valid_mask & ~invalid_mask))
            
            if has_tqdm:
                for idx, feat in enumerate(tqdm(features, desc="Applying heights")):
                    feat["properties"]["height"] = round(float(sampled_heights[idx]), 2)
            else:
                for idx, feat in enumerate(features):
                    feat["properties"]["height"] = round(float(sampled_heights[idx]), 2)
                
    except Exception as e:
        print(f"Error reading or sampling raster: {e}")
        sys.exit(1)
        
    print(f"Sampled valid heights for {count_valid} / {num_buildings} buildings.")

    # Save output GeoJSON
    print(f"Saving final 3D building polygons to {OUTPUT_PATH}...")
    output_geojson = {
        "type": "FeatureCollection",
        "name": "CMA_Buildings_3D",
        "features": footprints_data["features"]
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output_geojson, f)
        
    print(f"Successfully saved final 3D building data to {OUTPUT_PATH}!")

if __name__ == "__main__":
    main()
