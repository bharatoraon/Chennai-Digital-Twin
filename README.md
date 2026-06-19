# Chennai 3D Buildings Explorer (Chennai Digital Twin)

An interactive, high-performance 3D visualization and analysis tool for building heights and uses in the Chennai Metropolitan Area (CMA). This digital twin leverages the Google Open Buildings 2.5D dataset (footprints and heights) and visualizes over 525,000 structures in 3D using Maplibre GL JS.

## Features

- **Dynamic 3D Extrusions**: Visualize building heights in 3D, styled with rich color ramps.
- **Estimated Floor Height Slider**: Adjust the floor height parameter dynamically (from `3.0m` to `4.4m` per floor) to recalculate floor count estimates and metropolitan statistics in real-time.
- **Color Themes**: Toggle on the fly between **Color by Height** and **Color by Est. Use** (Residential, Commercial, Apartments, Industrial, Institutional).
- **Interactive Tooltips**: Hover over any building to view its estimated use class, height in meters, floor count, footprint area, confidence score, and Plus Code.
- **Glassmorphism Dashboard**: Live statistics summarizing total buildings, average height, average floor count, and tallest structures.
- **Fly-To Navigation**: Quickly navigate to dense urban hubs like Chennai Central and the OMR / IT Corridor.

---

## Repository Structure

```
├── index.html                  # Maplibre GL JS Web visualizer and UI
├── fast_extract.py             # Pipeline Stage 1: Stream, download and filter building footprints
├── join_heights.py             # Pipeline Stage 2: Vectorized GEE height raster intersection
├── classify_use.py             # Pipeline Stage 3: Area & height based heuristic use classifier
├── filter_geojson.py           # Pipeline Stage 4: Optimized dataset filters & disk cleanup
└── CMA.geojson                 # Chennai Metropolitan Area boundary shape (GeoJSON)
```

> **Note**: Large datasets (`cma_buildings_3d.geojson` and `cma_building_height_2022.tif`) are excluded from this repository via `.gitignore` to comply with GitHub's file size limits. They can be generated locally using the pipeline.

---

## Getting Started

### 1. Installation
Ensure you have Python 3 and the required libraries installed:
```bash
pip install numpy rasterio shapely tqdm
```

### 2. Generate the 3D Dataset
1. Place your GEE-exported building height raster (e.g. `cma_building_height_2022.tif`) in the workspace root directory.
2. Run Stage 1 (Extract Footprints):
   ```bash
   python3 fast_extract.py
   ```
3. Run Stage 2 (Join Heights):
   ```bash
   python3 join_heights.py
   ```
4. Run Stage 3 (Classify Building Use):
   ```bash
   python3 classify_use.py
   ```
5. Run Stage 4 (Optimize & Clean):
   ```bash
   python3 filter_geojson.py
   ```
   This will generate `cma_buildings_3d.geojson` (approx. 238 MB).

### 3. Run the Web Application
Launch a local development server in the repository directory:
```bash
python3 -m http.server 8000
```
Open your browser and navigate to:
[http://localhost:8000/](http://localhost:8000/)
