import xarray as xr
import rioxarray
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
from scipy.ndimage import label
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

# ==================================================
# 1. Load Nepal district shapefile
# ==================================================
shp_path = r"C:\Users\ACER\Downloads\Nepal Districts Shapefile Download\03_DISTRICT\DISTRICT.shp"
districts = gpd.read_file(shp_path)
districts = districts.to_crs(epsg=4326)

# ==================================================
# 2. Initialize variables for fire aggregation
# ==================================================
data_dir = r"S:\viirs\gridalligned_2024_VIIRS_daily_gridded_0.021_nc"
files = sorted([f"{data_dir}\\{f}" for f in os.listdir(data_dir) if f.endswith(".nc")])

fire_annual = None
frp_annual = None
dates = []
daily_fire_counts = []
nepal_mask = None

# ==================================================
# 3. Loop over daily files (PRE-MONSOON: Mar–May)
# ==================================================
for f in files:
    ds = xr.open_dataset(f)

    fire = ds["fire_count"].astype("float32")
    frp  = ds["frp_sum"].astype("float32")
    date = pd.to_datetime(ds["time"].values[0])

    if date.month in [3, 4, 5]:

        fire = fire.rio.write_crs("EPSG:4326")
        frp  = frp.rio.write_crs("EPSG:4326")

        if nepal_mask is None:
            tmp = fire.rio.clip(districts.geometry, all_touched=True, drop=False)
            nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

        fire_clip = fire.where(nepal_mask == 1)
        frp_clip  = frp.where(nepal_mask == 1)

        if fire_annual is None:
            fire_annual = fire_clip.copy()
            frp_annual  = frp_clip.copy()
        else:
            fire_annual += fire_clip
            frp_annual  += frp_clip

        daily_fire_counts.append(fire_clip.sum(dim=["lat","lon"]).item())
        dates.append(date)

    ds.close()

print("✔ Pre-monsoon aggregation completed")

# ==================================================
# 4. Compute 90th percentile thresholds (Nepal only)
# ==================================================
fire_thresh = fire_annual.where(nepal_mask == 1).quantile(0.90).item()
frp_thresh  = frp_annual.where(nepal_mask == 1).quantile(0.90).item()

# ==================================================
# 5. Create hotspot mask
# ==================================================
hotspot = (
    ((fire_annual >= fire_thresh) | (frp_annual >= frp_thresh))
    & (nepal_mask == 1)
)

# ==================================================
# 6. Connected Component Labeling (4-adjacency)
# ==================================================
binary = hotspot.fillna(0).astype(int)

structure = np.array([[0,1,0],
                      [1,1,1],
                      [0,1,0]])

labeled, n_clusters = label(binary.values, structure=structure)

labeled_da = xr.DataArray(
    labeled,
    coords=hotspot.coords,
    dims=hotspot.dims,
    name="hotspot_clusters"
).where(nepal_mask == 1)

print(f"✔ {n_clusters} hotspot clusters detected")

# ==================================================
# 7. Compute cluster regions (size & bounding boxes)
# ==================================================
regions = []

for cid in range(1, n_clusters + 1):
    mask = labeled == cid
    if mask.sum() == 0:
        continue

    lat_idx, lon_idx = np.where(mask)

    regions.append({
        "cluster": cid,
        "size": int(mask.sum()),
        "lat_min": float(hotspot.lat.values[lat_idx].min()),
        "lat_max": float(hotspot.lat.values[lat_idx].max()),
        "lon_min": float(hotspot.lon.values[lon_idx].min()),
        "lon_max": float(hotspot.lon.values[lon_idx].max())
    })

# Rank clusters by size
regions = sorted(regions, key=lambda x: x["size"], reverse=True)
top3 = regions[:3]

print("\nTop 3 clusters (NORMAL ranking):")
for r in top3:
    print(f"Cluster {r['cluster']} → {r['size']} pixels")

# ==================================================
# 8. Plot districts + hotspots + top3 bounding boxes
# ==================================================
fig, ax = plt.subplots(figsize=(3.54, 4.5))  # ~90 mm width

# Plot districts
districts.boundary.plot(ax=ax, linewidth=0.6, edgecolor="black")

# Plot annual fire counts (background)
fire_annual.plot(
    ax=ax, cmap="Greys", alpha=0.5, cbar_kwargs={"label": "Annual Fire Count"}
)

# Plot hotspot mask
hotspot.plot(ax=ax, cmap="Reds", alpha=0.4, add_colorbar=False)

# Plot top 3 cluster bounding boxes
for rank, r in enumerate(top3, start=1):
    rect_lon = [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]]
    rect_lat = [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]]
    ax.plot(rect_lon, rect_lat, color="cyan", linewidth=2)
    # Add cluster label
    ax.text(
        (r["lon_min"] + r["lon_max"])/2,
        (r["lat_min"] + r["lat_max"])/2
        f"R{rank}\nID{r['cluster']}",
        color="cyan",
        fontsize=6,
        ha="center",
        va="center",
        bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.1')
    )

# Add district names
for idx, row in districts.iterrows():
    centroid = row.geometry.centroid
    ax.text(
        centroid.x,
        centroid.y,
        str(row["DISTRICT"]),
        fontsize=5,
        ha="center",
        va="center",
        color="black",
        bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.1')
    )

# Formatting
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Top 3 Fire Hotspot Clusters (Pre-Monsoon 2024)", fontsize=8)
ax.set_aspect("equal", adjustable="box")
plt.tight_layout()

# Save figure
plt.savefig(
    r"S:\viirs\pictures\Clusters\2024\nepal_district_hotspots_2024.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()

### colors

import matplotlib.pyplot as plt

# --- Figure setup ---
fig, ax = plt.subplots(figsize=(7, 4.5))  # slightly wider figure

# --- Plot all labeled clusters with transparency ---
labeled_da.plot(
    ax=ax,
    cmap="tab20",       # distinct colors for clusters
    alpha=0.6,          # transparency so background is visible
    add_colorbar=False
)

# --- Plot top 3 cluster bounding boxes ---
for r in top3:
    rect_lon = [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]]
    rect_lat = [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]]
    ax.plot(rect_lon, rect_lat, color="cyan", linewidth=2, zorder=10)

    # Optional: add cluster ID inside rectangle
    ax.text(
        (r["lon_min"] + r["lon_max"])/2,
        (r["lat_min"] + r["lat_max"])/2,
        f"ID {r['cluster']}",
        color="cyan",
        fontsize=6,
        ha="center",
        va="center",
        bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.1'),
        zorder=11
    )

# --- Plot Nepal boundary ---
if districts.crs is not None:
    try:
        districts = districts.to_crs("EPSG:4326")
    except Exception:
        pass

districts.boundary.plot(
    ax=ax,
    edgecolor="black",
    linewidth=1.2,
    zorder=12
)

# --- Plot district names on top ---
for idx, row in districts.iterrows():
    centroid = row.geometry.centroid
    ax.text(
        centroid.x,
        centroid.y,
        str(row["DISTRICT"]),
        fontsize=5,                  # adjust as needed
        ha="center",
        va="center",
        color="black",
        bbox=dict(facecolor='white', alpha=0.6, boxstyle='round,pad=0.1'),
        zorder=13                     # above everything
    )

# --- Labels and formatting ---
ax.set_title("Hotspot Clusters in Nepal (Pre-Monsoon 2024)", fontsize=9)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal", adjustable="box")
plt.tight_layout()

# --- Optional: save figure ---
# plt.savefig(r"S:\viirs\pictures\Clusters\2024\nepal_labeled_clusters_2024.png", dpi=300, bbox_inches="tight")

plt.show()
