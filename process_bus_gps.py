import csv
import json
import os
import gzip
from datetime import datetime
from collections import defaultdict

# CMA bounding box
LAT_MIN, LAT_MAX = 12.6, 13.35
LON_MIN, LON_MAX = 79.6, 80.4

# Config
SAMPLE_INTERVAL_SEC = 120  # 1 ping per 2 minutes per bus
MIN_PINGS = 3              # minimum pings to include a bus

DATA_DIR   = "/Volumes/Sandisk SSD/Google_building/Bus_GPS_Data"
OUTPUT_PATH = "/Volumes/Sandisk SSD/Google_building/bus_trips.json.gz"

CSV_FILES = sorted([
    os.path.join(DATA_DIR, f)
    for f in os.listdir(DATA_DIR)
    if f.endswith('.csv')
])

print(f"Processing {len(CSV_FILES)} CSV files...")

# Store pings per device: {deviceId: [(unix_ts, lat, lon, route)]}
device_pings = defaultdict(list)

for csv_path in CSV_FILES:
    fname = os.path.basename(csv_path)
    print(f"  Reading {fname} ({os.path.getsize(csv_path)/(1024*1024):.0f} MB)...")
    
    count = 0
    kept = 0
    
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
            
            # Skip parked buses
            if row.get('ign_status', '') != 'IGNON':
                continue
            
            # Parse coordinates
            try:
                lat = float(row['lat'])
                lon = float(row['long'])
            except (ValueError, KeyError):
                continue
            
            # Filter to CMA
            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                continue
            
            # Parse timestamp
            ts_str = row.get('timestamp', '').strip()
            if not ts_str:
                continue
            try:
                dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                unix_ts = int(dt.timestamp())
            except ValueError:
                continue
            
            device_id = row.get('deviceId', '').strip()
            if not device_id:
                continue
            
            route = row.get('routeNumber', '').strip() or '?'
            
            device_pings[device_id].append((unix_ts, lat, lon, route))
            kept += 1
    
    print(f"    → {count:,} rows read, {kept:,} kept ({kept/max(count,1)*100:.1f}%)")

print(f"\nTotal unique devices: {len(device_pings):,}")

# Build trips with temporal sampling
print("Building sampled trips...")

trips = {}
skipped_too_few = 0

for device_id, pings in device_pings.items():
    # Sort by time
    pings.sort(key=lambda x: x[0])
    
    # Determine route (most common)
    routes = [p[3] for p in pings if p[3] != '?']
    route = max(set(routes), key=routes.count) if routes else '?'
    
    # Temporal sampling: keep 1 ping per SAMPLE_INTERVAL_SEC
    sampled = []
    last_ts = -999999
    for ts, lat, lon, _ in pings:
        if ts - last_ts >= SAMPLE_INTERVAL_SEC:
            sampled.append([round(lon, 5), round(lat, 5), ts])
            last_ts = ts
    
    if len(sampled) < MIN_PINGS:
        skipped_too_few += 1
        continue
    
    trips[device_id] = {
        'r': route,
        'c': sampled
    }

print(f"Skipped {skipped_too_few:,} devices with < {MIN_PINGS} pings")
print(f"Kept {len(trips):,} bus trips")

print(f"\nWriting gzipped JSON to {OUTPUT_PATH}...")
json_bytes = json.dumps(trips, separators=(',', ':')).encode('utf-8')
with gzip.open(OUTPUT_PATH, 'wb', compresslevel=9) as f:
    f.write(json_bytes)

raw_mb  = len(json_bytes) / (1024 * 1024)
size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
print(f"✅ Done! bus_trips.json.gz = {size_mb:.2f} MB (raw JSON was {raw_mb:.1f} MB)")
print(f"   Total buses: {len(trips):,}")

# Print time range
all_ts = [p[2] for t in trips.values() for p in t['c']]
if all_ts:
    t_min = datetime.fromtimestamp(min(all_ts))
    t_max = datetime.fromtimestamp(max(all_ts))
    print(f"   Time range: {t_min} → {t_max}")

# Stats
ping_counts = [len(t['c']) for t in trips.values()]
print(f"   Avg pings/bus: {sum(ping_counts)/len(ping_counts):.1f}")
print(f"   Max pings/bus: {max(ping_counts)}")
