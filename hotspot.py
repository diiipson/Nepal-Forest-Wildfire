import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from libpysal.weights import lat2W
from esda import G_Local
from shapely.geometry import Polygon, Point
from skimage import measure
import geopandas as gpd

# --------------------------------------------------
# 1. DATA DIRECTORY
# --------------------------------------------------
data_dir = r"S:\viirs\VIIRS_daily_gridded1_nc"
files = sorted([
    os.path.join(data_dir, f)
    for f in os.listdir(data_dir)
    if f.endswith(".nc") and "202104" in f
])

# --------------------------------------------------
# 2. AGGREGATE APRIL DATA
# --------------------------------------------------
fire_count = None
frp_sum = None
frp_max = None
lat = lon = None

for f in files:
    ds = xr.open_dataset(f)

    if fire_count is None:
        fire_count = ds["fire_count"].copy()
        frp_sum = ds["frp_sum"].copy()
        frp_max = ds["frp_max"].copy()
        lat = ds["lat"].values
        lon = ds["lon"].values
    else:
        fire_count += ds["fire_count"]
        frp_sum += ds["frp_sum"]
        frp_max = xr.ufuncs.maximum(frp_max, ds["frp_max"])

    ds.close()

print("✔ April aggregation completed")

# --------------------------------------------------
# 3. GETIS–ORD Gi*
# --------------------------------------------------
nlat, nlon = fire_count.shape
w = lat2W(nlat, nlon)

fire_flat = fire_count.values.flatten()
gi = G_Local(fire_flat, w, transform="r", star=1)
gi_z = gi.Zs.reshape(nlat, nlon)

# --------------------------------------------------
# 4. ADAPTIVE HOTSPOT EXTRACTION (ENSURE ≥3)
# --------------------------------------------------
z_threshold = 2.5     # start strict
min_threshold = 1.65 # do not go below 90%
polygons = []

while z_threshold >= min_threshold:
    mask = gi_z >= z_threshold
    contours = measure.find_contours(mask.astype(int), 0.5)
    polygons = []

    for contour in contours:
        coords = []
        for y, x in contour:
            i = int(round(y))
            j = int(round(x))
            i = min(max(i, 0), len(lat)-1)
            j = min(max(j, 0), len(lon)-1)
            coords.append((lon[j], lat[i]))

        poly = Polygon(coords)
        if poly.is_valid and poly.area > 0:
            polygons.append(poly)

    if len(polygons) >= 3:
        break

    z_threshold -= 0.1

# Sort by area and keep top 3
polygons = sorted(polygons, key=lambda p: p.area, reverse=True)[:3]

print(f"✔ Using Z ≥ {z_threshold:.2f}")
print(f"✔ Identified {len(polygons)} fire hotspots")

# --------------------------------------------------
# 5. SAVE SHAPEFILE
# --------------------------------------------------
gdf = gpd.GeoDataFrame(
    {"Hotspot_ID": [1, 2, 3]},
    geometry=polygons,
    crs="EPSG:4326"
)

shp_path = os.path.join(
    data_dir, "VIIRS_April2021_Fire_Hotspots_3_Gi.shp"
)
gdf.to_file(shp_path)
print(f"✔ Shapefile saved: {shp_path}")

# --------------------------------------------------
# 6. PLOT APRIL FIRE COUNT + 3 HOTSPOTS
# --------------------------------------------------
plt.figure(figsize=(9, 7))
plt.pcolormesh(
    lon, lat, fire_count,
    cmap="hot", shading="auto", alpha=0.7
)
plt.colorbar(label="April Fire Count")

for i, poly in enumerate(polygons, start=1):
    x, y = poly.exterior.xy
    plt.plot(x, y, linewidth=2, label=f"Hotspot {i}")

plt.legend()
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("VIIRS Pre-Monsoon Fire Hotspots (April 2021) – Nepal")
plt.show()

# --------------------------------------------------
# 7. HOTSPOT STATISTICS
# --------------------------------------------------
print("\nHotspot severity summary:")

for i, poly in enumerate(polygons, start=1):
    mask = np.zeros_like(fire_count.values, dtype=bool)

    for ii in range(len(lat)):
        for jj in range(len(lon)):
            if poly.contains(Point(lon[jj], lat[ii])):
                mask[ii, jj] = True

    total_fire = fire_count.values[mask].sum()
    total_frp = frp_sum.values[mask].sum()
    peak_frp = frp_max.values[mask].max() if np.any(mask) else np.nan

    print(
        f"Hotspot {i}: "
        f"Fire Count={total_fire}, "
        f"FRP Sum={total_frp:.1f}, "
        f"FRP Max={peak_frp:.1f}"
    )


import xarray as xr
data_dir = r"S:\viirs\VIIRS_daily_gridded1_nc\VIIRS_FIRE_NEPAL_20210408.nc"
ds= xr.open_dataset(data_dir)
print(ds.info)
print(ds["lat"])
