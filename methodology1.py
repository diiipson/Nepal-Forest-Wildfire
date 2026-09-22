import xarray as xr
import rioxarray
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
import pandas as pd
import glob
import os

# ==================================================
# 1. Paths
# ==================================================
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
shape_file = r"C:\Users\ACER\Downloads\boundary.shp"

files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
if not files:
    raise FileNotFoundError("No NetCDF files found")

nepal = gpd.read_file(shape_file).to_crs("EPSG:4326")

# ==================================================
# 2. Initialize
# ==================================================
fire_annual = None
frp_annual = None
dates = []
daily_fire_counts = []
nepal_mask = None

# ==================================================
# 3. Loop over daily files (PRE-MONSOON)
# ==================================================
for i, f in enumerate(files):
    ds = xr.open_dataset(f)

    fire = ds["fire_count"].astype("float32")
    frp  = ds["frp_sum"].astype("float32")
    date = pd.to_datetime(ds["time"].values[0])

    if date.month in [3, 4, 5]:

        fire = fire.rio.write_crs("EPSG:4326")
        frp  = frp.rio.write_crs("EPSG:4326")

        # Create Nepal mask ONCE
        if nepal_mask is None:
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
            nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

        fire_clip = fire.where(nepal_mask == 1)
        frp_clip  = frp.where(nepal_mask == 1)

        # Annual aggregation
        if fire_annual is None:
            fire_annual = fire_clip.copy()
            frp_annual  = frp_clip.copy()
        else:
            fire_annual += fire_clip
            frp_annual  += frp_clip

        # Daily fire count (ONLY Nepal)
        daily_fire_counts.append(fire_clip.sum(dim=["lat", "lon"]).item())
        dates.append(date)

    ds.close()

print("✔ Pre-monsoon aggregation completed")

# ==================================================
# 4. Percentiles (ONLY INSIDE NEPAL)
# ==================================================
fire_thresh = fire_annual.where(nepal_mask == 1).quantile(0.95).item()
frp_thresh  = frp_annual.where(nepal_mask == 1).quantile(0.95).item()

# ==================================================
# 5. Hotspot mask (Nepal only)
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
# 7. Extract cluster sizes
# ==================================================
clusters = []
for cid in range(1, n_clusters + 1):
    size = np.sum(labeled == cid)
    if size > 0:
        clusters.append({"cluster": cid, "size": size})

clusters = sorted(clusters, key=lambda x: x["size"], reverse=True)
top3 = clusters[:3]

print("\nTop 3 clusters:")
for c in top3:
    print(f"Cluster {c['cluster']} → {c['size']} pixels")

# ==================================================
# 8. Map: Annual fire + hotspots
# ==================================================
fig, ax = plt.subplots(figsize=(10, 8))

fire_annual.plot(
    ax=ax,
    cmap="Greys",
    alpha=0.6,
    cbar_kwargs={"label": "Annual Fire Count"}
)

hotspot.plot(
    ax=ax,
    cmap="Reds",
    alpha=0.6,
    add_colorbar=False
)

nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.5)

ax.set_title("Pre-Monsoon Fire Hotspots (Nepal, 2021)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 9. Time series plot
# ==================================================
plt.figure(figsize=(14, 5))
plt.plot(dates, daily_fire_counts, color="firebrick", lw=1)
plt.title("Daily VIIRS Fire Count Inside Nepal (Pre-Monsoon 2021)")
plt.xlabel("Date")
plt.ylabel("Fire Count")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# ==================================================
# 10. Labeled CCL grid plot (REQUESTED)
# ==================================================
plt.figure(figsize=(10, 8))

labeled_da.plot(
    cmap="tab20",
    add_colorbar=True,
    cbar_kwargs={"label": "Cluster ID"}
)

nepal.boundary.plot(
    ax=plt.gca(),
    edgecolor="black",
    linewidth=1.2
)

plt.title("Connected-Component Labeled Hotspot Clusters (Nepal, 2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()


################################################################################
import xarray as xr
import rioxarray
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
import pandas as pd
import glob
import os

# ==================================================
# 1. Paths
# ==================================================
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
shape_file = r"C:\Users\ACER\Downloads\boundary.shp"

files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
if not files:
    raise FileNotFoundError("No NetCDF files found")

nepal = gpd.read_file(shape_file).to_crs("EPSG:4326")

# ==================================================
# 2. Initialize
# ==================================================
fire_annual = None
frp_annual = None
dates = []
daily_fire_counts = []
nepal_mask = None

# ==================================================
# 3. Loop over daily files (PRE-MONSOON)
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
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
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
# 4. Percentiles (Nepal only)
# ==================================================
fire_thresh = fire_annual.where(nepal_mask == 1).quantile(0.95).item()
frp_thresh  = frp_annual.where(nepal_mask == 1).quantile(0.95).item()

# ==================================================
# 5. Hotspot mask (Nepal only)
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

# labeled, n_clusters = label(binary.values, structure=structure)
labeled, n_clusters = label(hotspot.values)

labeled_da = xr.DataArray(
    labeled,
    coords=hotspot.coords,
    dims=hotspot.dims,
    name="hotspot_clusters"
).where(nepal_mask == 1)

print(f"✔ {n_clusters} hotspot clusters detected")

# ==================================================
# 7. Extract cluster properties
# ==================================================
regions = []

for cid in range(1, n_clusters + 1):
    mask = labeled == cid
    if np.sum(mask) == 0:
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

regions = sorted(regions, key=lambda x: x["size"], reverse=True)
top3 = regions[:3]

print("\nTop 3 clusters:")
for r in top3:
    print(f"Cluster {r['cluster']} → {r['size']} pixels")

# ==================================================
# 8. Map with Top-3 bounding boxes
# ==================================================
fig, ax = plt.subplots(figsize=(10,8))

fire_annual.plot(
    ax=ax, cmap="Greys", alpha=0.6,
    cbar_kwargs={"label": "Annual Fire Count"}
)

hotspot.plot(ax=ax, cmap="Reds", alpha=0.6, add_colorbar=False)
nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.5)

for r in top3:
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
        color="cyan", linewidth=2
    )

ax.set_title("Top 3 Pre-Monsoon Fire Hotspot Clusters (Nepal)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 9. Daily fire count time series
# ==================================================
plt.figure(figsize=(14,5))
plt.plot(dates, daily_fire_counts, color="firebrick", lw=1)
plt.title("Daily VIIRS Fire Count Inside Nepal (Pre-Monsoon 2021)")
plt.xlabel("Date")
plt.ylabel("Fire Count")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# ==================================================
# 10. Labeled cluster grid (full Nepal)
# ==================================================
plt.figure(figsize=(10,8))
labeled_da.plot(
    cmap="tab20",
    add_colorbar=True,
    cbar_kwargs={"label": "Cluster ID"}
)
nepal.boundary.plot(ax=plt.gca(), edgecolor="black", linewidth=1.2)
plt.title("Connected-Component Labeled Hotspot Clusters (Nepal)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 11. Zoomed views of TOP 3 clusters
# ==================================================
import rioxarray  # move this to the TOP of your file, not inside the loop

for i, r in enumerate(top3, start=1):
    zoom = labeled_da.sel(
        lat=slice(r["lat_min"], r["lat_max"]),
        lon=slice(r["lon_min"], r["lon_max"])
    )

    plt.figure(figsize=(6, 6))
    zoom.plot(cmap="tab20", add_colorbar=False)
    plt.grid(True, linewidth=0.3)
    plt.title(f"Zoomed Cluster {i} (ID {r['cluster']})")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()

############# before leqaving ############
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
import pandas as pd
import glob
import os

# ==================================================
# 1. Paths
# ==================================================
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
shape_file = r"C:\Users\ACER\Downloads\boundary.shp"

files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
if not files:
    raise FileNotFoundError("No NetCDF files found")

nepal = gpd.read_file(shape_file).to_crs("EPSG:4326")

# ==================================================
# 2. Initialize
# ==================================================
fire_annual = None
frp_annual = None
dates = []
daily_fire_counts = []
nepal_mask = None

# ==================================================
# 3. Loop over daily files (PRE-MONSOON)
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
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
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
# 4. Percentiles (Nepal only)
# ==================================================
fire_thresh = fire_annual.where(nepal_mask == 1).quantile(0.90).item()
frp_thresh  = frp_annual.where(nepal_mask == 1).quantile(0.90).item()

# ==================================================
# 5. Hotspot mask (Nepal only)
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
# 7. NORMAL cluster ranking (by size only)
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

# Rank normally (no overlap filtering)
regions = sorted(regions, key=lambda x: x["size"], reverse=True)
top3 = regions[:3]

print("\nTop 3 clusters (NORMAL ranking):")
for r in top3:
    print(f"Cluster {r['cluster']} → {r['size']} pixels")

# ==================================================
# 8. Map with hotspots + bounding boxes
# ==================================================
fig, ax = plt.subplots(figsize=(10,8))

fire_annual.plot(
    ax=ax, cmap="Greys", alpha=0.6,
    cbar_kwargs={"label": "Annual Fire Count"}
)

hotspot.plot(ax=ax, cmap="Reds", alpha=0.6, add_colorbar=False)
nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.5)

for r in top3:
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
        color="cyan", linewidth=2
    )

ax.set_title("Top 3 Fire Hotspot Clusters (Normal Ranking)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 9. Daily fire count time series
# ==================================================
plt.figure(figsize=(14,5))
plt.plot(dates, daily_fire_counts, color="firebrick", lw=1)
plt.title("Daily VIIRS Fire Count Inside Nepal (Pre-Monsoon 2021)")
plt.xlabel("Date")
plt.ylabel("Fire Count")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# ==================================================
# 10. Labeled cluster grid
# ==================================================
import matplotlib.pyplot as plt

# ==================================================
# 10. Labeled cluster grid with bounding boxes
# ==================================================

# --- Create figure and axis explicitly ---
fig, ax = plt.subplots(figsize=(10, 8))

# --- Plot labeled clusters ---
labeled_da.plot(
    ax=ax,
    cmap="tab20",
    add_colorbar=False,
    cbar_kwargs={"label": "Cluster ID"}
)

# --- Plot bounding boxes for top clusters ---
for r in top3:
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
        color="cyan",
        linewidth=2,
        zorder=10
    )

# --- Ensure CRS consistency ---
# (only needed if Nepal CRS differs)
if nepal.crs is not None:
    try:
        nepal = nepal.to_crs("EPSG:4326")
    except Exception:
        pass

# --- Plot Nepal boundary ---
nepal.boundary.plot(
    ax=ax,
    edgecolor="black",
    linewidth=1.2,
    zorder=11
)

# --- Labels and layout ---
#ax.set_title("Connected-Component Labeled Hotspot Clusters (Nepal)")
ax.set_title("")

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

plt.tight_layout()
plt.show()


# ==================================================
# 11. Zoomed plots of top 3 clusters
# ==================================================
# ==================================================
# 11. Zoomed plots of top 3 clusters (show grid resolution)

# ==================================================


for i, r in enumerate(top3, start=1):

    # --- Select zoomed region ---
    zoom = labeled_da.sel(
        lat=slice(r["lat_min"], r["lat_max"]),
        lon=slice(r["lon_min"], r["lon_max"])
    )

    # --- Create figure and axis ---
    fig, ax = plt.subplots(figsize=(6, 6))

    # --- Plot cluster labels ---
    zoom.plot(
        ax=ax,
        cmap="tab20",
        add_colorbar=False
    )

    # --- Overlay original grid resolution (pixel grid) ---
    ax.set_xticks(zoom.lon.values, minor=True)
    ax.set_yticks(zoom.lat.values, minor=True)

    ax.grid(
        which="minor",
        color="black",
        linewidth=0.3
    )

    # Optional: keep major grid subtle
    ax.grid(
        which="major",
        color="gray",
        linewidth=0.2,
        linestyle="--"
    )

    # --- Labels and title ---
    ax.set_title(f"Zoomed Cluster Rank {i} (ID {r['cluster']})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    plt.tight_layout()
    plt.show()


#latlon information of top 3 hotspot
for i, r in enumerate(top3, start=1):
    print(f"Cluster rank {i} (ID {r['cluster']}):")
    print(f"  lat_min = {r['lat_min']}")
    print(f"  lat_max = {r['lat_max']}")
    print(f"  lon_min = {r['lon_min']}")
    print(f"  lon_max = {r['lon_max']}")
    print(f"  Cluster size S_k = {r['size']}")  
# ID of the top cluster
for i, r in enumerate(top3, start=1):
    cluster_id = r['cluster']

    # Select only the bounding box region
    zoom = labeled_da.sel(
        lat=slice(r["lat_min"], r["lat_max"]),
        lon=slice(r["lon_min"], r["lon_max"])
    )

    # Mask to show only the cluster cells
    cluster_mask = zoom == cluster_id

    # Plot
    plt.figure(figsize=(6,6))
    cluster_mask.plot(
        cmap="Oranges",   # Color for hotspot cells
        add_colorbar=False
    )

    # Overlay grid (optional, like before)
    ax = plt.gca()
    ax.set_xticks(zoom.lon.values, minor=True)
    ax.set_yticks(zoom.lat.values, minor=True)
    ax.grid(which="minor", color="black", linewidth=0.3)
    ax.grid(which="major", color="gray", linewidth=0.2, linestyle="--")

    # Overlay Nepal boundary
    nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.2)

    plt.title(f"Zoomed Top Cluster {i} (ID {cluster_id}, Size {r['size']})")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()





############ SAME COLOR ############
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# --- Global cluster info (shared by all plots) ---
cluster_ids = np.unique(labeled_da.values[~np.isnan(labeled_da.values)])

cmap = plt.get_cmap("tab20", len(cluster_ids))
bounds = np.arange(cluster_ids.min(), cluster_ids.max() + 2) - 0.5
norm = mcolors.BoundaryNorm(bounds, cmap.N)
fig, ax = plt.subplots(figsize=(10, 8))

# --- Plot labeled clusters (fixed colors) ---
labeled_da.plot(
    ax=ax,
    cmap=cmap,
    norm=norm,
    add_colorbar=False
)

# --- Plot bounding boxes for top clusters ---
for r in top3:
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
        color="cyan",
        linewidth=2,
        zorder=10
    )

# --- CRS consistency ---
if nepal.crs is not None:
    try:
        nepal = nepal.to_crs("EPSG:4326")
    except Exception:
        pass

# --- Plot Nepal boundary ---
nepal.boundary.plot(
    ax=ax,
    edgecolor="black",
    linewidth=1.2,
    zorder=11
)

# --- Labels (no title) ---
ax.set_title("")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

plt.tight_layout()
plt.show()


for i, r in enumerate(top3, start=1):

    # --- Select zoomed region ---
    zoom = labeled_da.sel(
        lat=slice(r["lat_min"], r["lat_max"]),
        lon=slice(r["lon_min"], r["lon_max"])
    )

    fig, ax = plt.subplots(figsize=(6, 6))

    # --- Plot zoomed clusters (same cmap + norm) ---
    zoom.plot(
        ax=ax,
        cmap=cmap,
        norm=norm,
        add_colorbar=False
    )

    # --- Overlay grid resolution ---
    ax.set_xticks(zoom.lon.values, minor=True)
    ax.set_yticks(zoom.lat.values, minor=True)

    ax.grid(which="minor", color="black", linewidth=0.3)
    ax.grid(which="major", color="gray", linewidth=0.2, linestyle="--")

    # --- Labels ---
    #ax.set_title(f"Zoomed Cluster Rank {i} (ID {r['cluster']})")
    ax.set_title("")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    plt.tight_layout()
    plt.show()

