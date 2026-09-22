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
data_dir = r"S:\viirs\gridalligned_2021_VIIRS_daily_gridded_0.021_nc"
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
daily_fire_counts_all = []    # whole year
dates_all = []

# ==================================================
# 3. Loop over daily files (PRE-MONSOON)
# ==================================================
for f in files:
    ds = xr.open_dataset(f)

    fire = ds["fire_count"].astype("float32")
    frp  = ds["frp_sum"].astype("float32")
    date = pd.to_datetime(ds["time"].values[0])

    # --- Write CRS ---
    fire = fire.rio.write_crs("EPSG:4326")
    frp  = frp.rio.write_crs("EPSG:4326")

    # --- Create Nepal mask once ---
    if nepal_mask is None:
        tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
        nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

    # --- Clip to Nepal ---
    fire_clip = fire.where(nepal_mask == 1)
    frp_clip  = frp.where(nepal_mask == 1)

    # --- 🔹 DAILY COUNT (WHOLE YEAR) ---
    daily_fire_counts_all.append(
        fire_clip.sum(dim=["lat", "lon"]).item()
    )
    dates_all.append(date)

    # --- 🔹 PRE-MONSOON ONLY (Mar–May) ---
    if date.month in [3, 4, 5]:

        if fire_annual is None:
            fire_annual = fire_clip.copy()
            frp_annual  = frp_clip.copy()
        else:
            fire_annual += fire_clip
            frp_annual  += frp_clip

        daily_fire_counts.append(
            fire_clip.sum(dim=["lat", "lon"]).item()
        )
        dates.append(date)

    ds.close()

print("✔ Pre-monsoon aggregation completed")
print("✔ Whole-year daily fire counts completed")

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

##whole year plot
plt.figure(figsize=(7,4.5))
plt.plot(dates_all, daily_fire_counts_all, color="firebrick", lw=1)
#plt.title("Daily VIIRS Fire Count Inside Nepal ")
plt.xlabel("Date")
plt.ylabel("Fire Count")
plt.grid(alpha=0.3)
plt.tight_layout()
# plt.savefig(
#      r"S:\viirs\pictures\fire_count\2021.png",
#      dpi=1000,
#      bbox_inches="tight"
#  )
# plt.show()


# ==================================================
# 10. Labeled cluster grid
# ==================================================
import matplotlib.pyplot as plt

# ==================================================
# 10. Labeled cluster grid with bounding boxes
# ==================================================

# --- Create figure and axis explicitly ---
fig, ax = plt.subplots(figsize=(7, 4.5))

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

# plt.savefig(
#     r"S:\viirs\pictures\Clusters\2024\figure_name.png",
#     dpi=300,
#     bbox_inches="tight"
# )
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
    
    # --- Mask background (cluster 0) ---
    masked_zoom = np.ma.masked_where(zoom.values == 0, zoom.values)
    
    # --- Compute lat/lon edges ---
    # Use lat_bnds and lon_bnds if available
    try:
        lat_edges = np.zeros(zoom.lat_bnds.shape[0] + 1)
        lat_edges[:-1] = zoom.lat_bnds[:, 0]
        lat_edges[-1] = zoom.lat_bnds[-1, 1]

        lon_edges = np.zeros(zoom.lon_bnds.shape[0] + 1)
        lon_edges[:-1] = zoom.lon_bnds[:, 0]
        lon_edges[-1] = zoom.lon_bnds[-1, 1]
    except AttributeError:
        # If no bounds, approximate edges using midpoints
        lat = zoom.lat.values
        lon = zoom.lon.values
        lat_edges = np.zeros(len(lat) + 1)
        lon_edges = np.zeros(len(lon) + 1)

        lat_edges[1:-1] = (lat[:-1] + lat[1:]) / 2
        lat_edges[0] = lat[0] - (lat[1] - lat[0]) / 2
        lat_edges[-1] = lat[-1] + (lat[-1] - lat[-2]) / 2

        lon_edges[1:-1] = (lon[:-1] + lon[1:]) / 2
        lon_edges[0] = lon[0] - (lon[1] - lon[0]) / 2
        lon_edges[-1] = lon[-1] + (lon[-1] - lon[-2]) / 2

    # --- Create figure ---
    fig, ax = plt.subplots(figsize=(6,6))
    
    # --- Create meshgrid for edges ---
    lon_grid, lat_grid = np.meshgrid(lon_edges, lat_edges)

    # --- Plot with pcolormesh ---
    cmap = plt.cm.tab20.copy()
    cmap.set_bad(color='white')

    im = ax.pcolormesh(
        lon_grid,
        lat_grid,
        masked_zoom,
        cmap=cmap,
        edgecolor='black',  # optional: draw grid lines
        linewidth=0.3
    )

    # --- Optional: overlay minor grid lines exactly ---
    for lat in lat_edges:
        ax.axhline(lat, color='black', linewidth=0.3, linestyle=':')
    for lon in lon_edges:
        ax.axvline(lon, color='black', linewidth=0.3, linestyle=':')

    # --- Labels, title, colorbar ---
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"Zoomed Cluster Rank {i} (ID {r['cluster']})")

    cbar = plt.colorbar(im, ax=ax, ticks=np.arange(zoom.max().item()+1))
    cbar.set_label('Cluster ID')

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


############# same color

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# --- Global cluster info (shared by all plots) ---
cluster_values = labeled_da.values
cluster_ids = np.unique(cluster_values[~np.isnan(cluster_values)])

# Include 0 (background) in colormap
all_ids = np.insert(cluster_ids, 0, 0) if 0 not in cluster_ids else cluster_ids

cmap = plt.get_cmap("tab20", len(all_ids))
bounds = np.arange(all_ids.min(), all_ids.max() + 2) - 0.5
norm = mcolors.BoundaryNorm(bounds, cmap.N)

# --- Compute lat/lon edges for full map ---
try:
    lat_edges = np.zeros(labeled_da.lat_bnds.shape[0] + 1)
    lat_edges[:-1] = labeled_da.lat_bnds[:, 0]
    lat_edges[-1] = labeled_da.lat_bnds[-1, 1]

    lon_edges = np.zeros(labeled_da.lon_bnds.shape[0] + 1)
    lon_edges[:-1] = labeled_da.lon_bnds[:, 0]
    lon_edges[-1] = labeled_da.lon_bnds[-1, 1]
except AttributeError:
    lat = labeled_da.lat.values
    lon = labeled_da.lon.values
    lat_edges = np.zeros(len(lat) + 1)
    lon_edges = np.zeros(len(lon) + 1)
    lat_edges[1:-1] = (lat[:-1] + lat[1:]) / 2
    lat_edges[0] = lat[0] - (lat[1] - lat[0]) / 2
    lat_edges[-1] = lat[-1] + (lat[-1] - lat[-2]) / 2
    lon_edges[1:-1] = (lon[:-1] + lon[1:]) / 2
    lon_edges[0] = lon[0] - (lon[1] - lon[0]) / 2
    lon_edges[-1] = lon[-1] + (lon[-1] - lon[-2]) / 2

# --- Meshgrid for pcolormesh ---
lon_grid, lat_grid = np.meshgrid(lon_edges, lat_edges)

# --- Full global map ---
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.pcolormesh(
    lon_grid,
    lat_grid,
    cluster_values,    # include 0 values now
    cmap=cmap,
    norm=norm,
    edgecolor='black',  # optional: cell borders
    linewidth=0.2
)

# --- Overlay top cluster bounding boxes ---
for r in top3:
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"], r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"], r["lat_max"], r["lat_min"]],
        color="cyan",
        linewidth=2,
        zorder=10
    )

# --- Nepal boundary ---
if nepal.crs is not None:
    try:
        nepal = nepal.to_crs("EPSG:4326")
    except Exception:
        pass
nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.2, zorder=11)

# --- Labels ---
ax.set_title("")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
cbar = plt.colorbar(im, ax=ax, ticks=np.arange(all_ids.min(), all_ids.max()+1))
cbar.set_label('Cluster ID')

plt.tight_layout()
plt.show()

# --- Zoomed maps for top clusters ---
for i, r in enumerate(top3, start=1):
    
    zoom = labeled_da.sel(
        lat=slice(r["lat_min"], r["lat_max"]),
        lon=slice(r["lon_min"], r["lon_max"])
    )
    
    # Include background (0) pixels
    zoom_values = zoom.values

    # Compute edges for zoomed region
    try:
        lat_edges = np.zeros(zoom.lat_bnds.shape[0] + 1)
        lat_edges[:-1] = zoom.lat_bnds[:, 0]
        lat_edges[-1] = zoom.lat_bnds[-1, 1]
        lon_edges = np.zeros(zoom.lon_bnds.shape[0] + 1)
        lon_edges[:-1] = zoom.lon_bnds[:, 0]
        lon_edges[-1] = zoom.lon_bnds[-1, 1]
    except AttributeError:
        lat = zoom.lat.values
        lon = zoom.lon.values
        lat_edges = np.zeros(len(lat) + 1)
        lon_edges = np.zeros(len(lon) + 1)
        lat_edges[1:-1] = (lat[:-1] + lat[1:]) / 2
        lat_edges[0] = lat[0] - (lat[1] - lat[0]) / 2
        lat_edges[-1] = lat[-1] + (lat[-1] - lat[-2]) / 2
        lon_edges[1:-1] = (lon[:-1] + lon[1:]) / 2
        lon_edges[0] = lon[0] - (lon[1] - lon[0]) / 2
        lon_edges[-1] = lon[-1] + (lon[-1] - lon[-2]) / 2
    
    lon_grid, lat_grid = np.meshgrid(lon_edges, lat_edges)
    
    fig, ax = plt.subplots(figsize=(3.6,3.6))
    im = ax.pcolormesh(
        lon_grid,
        lat_grid,
        zoom_values,      # include background 0
        cmap=cmap,
        norm=norm,
        edgecolor='black',
        linewidth=0.2
    )
    
    # ax.set_title(f"Zoomed Cluster Rank {i} (ID {r['cluster']})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    
    # cbar = plt.colorbar(im, ax=ax, ticks=np.arange(all_ids.min(), all_ids.max()+1))
    # cbar.set_label('Cluster ID')
    
    plt.tight_layout()
    plt.savefig(
    fr"S:\viirs\pictures\Clusters\2021\new_cluster{i}.png",
    dpi=1000,
    bbox_inches="tight"
)
    plt.show()

import numpy as np

R = 6371.0  # Earth radius in km

for i, r in enumerate(top3, start=1):
    lat_min = r["lat_min"]
    lat_max = r["lat_max"]
    lon_min = r["lon_min"]
    lon_max = r["lon_max"]

    # Convert degrees to radians
    lat_min_rad = np.deg2rad(lat_min)
    lat_max_rad = np.deg2rad(lat_max)
    lon_min_rad = np.deg2rad(lon_min)
    lon_max_rad = np.deg2rad(lon_max)

    # Area calculation (km^2)
    area_km2 = (
        R**2
        * (lon_max_rad - lon_min_rad)
        * (np.sin(lat_max_rad) - np.sin(lat_min_rad))
    )

    print(f"Cluster rank {i} (ID {r['cluster']}):")
    print(f"  lat_min = {lat_min}")
    print(f"  lat_max = {lat_max}")
    print(f"  lon_min = {lon_min}")
    print(f"  lon_max = {lon_max}")
    print(f"  Cluster size S_k = {r['size']}")
    print(f"  Area ≈ {area_km2:.2f} km²\n")


######## SYNDER FORMULA #########
import numpy as np

# Earth radius (km)
R = 6371.0

def compute_cluster_area_km2(labeled_da, cluster_info):
    """
    Compute pixel-based area (km^2) of a single cluster on a lat-lon grid.

    Parameters
    ----------
    labeled_da : xarray.DataArray
        Labeled grid where each pixel contains a cluster ID.
    cluster_info : dict
        Dictionary with keys:
        'cluster', 'lat_min', 'lat_max', 'lon_min', 'lon_max', 'size'

    Returns
    -------
    area_km2 : float
        Total area of the cluster in km^2.
    """

    cluster_id = cluster_info["cluster"]

    # Restrict to bounding box for efficiency
    zoom = labeled_da.sel(
        lat=slice(cluster_info["lat_min"], cluster_info["lat_max"]),
        lon=slice(cluster_info["lon_min"], cluster_info["lon_max"])
    )

    # Mask: only cluster pixels
    mask = zoom.values == cluster_id

    # Coordinates
    lat = zoom.lat.values
    lon = zoom.lon.values

    # ---- Compute pixel edges ----
    lat_edges = np.zeros(len(lat) + 1)
    lon_edges = np.zeros(len(lon) + 1)

    lat_edges[1:-1] = (lat[:-1] + lat[1:]) / 2
    lat_edges[0] = lat[0] - (lat[1] - lat[0]) / 2
    lat_edges[-1] = lat[-1] + (lat[-1] - lat[-2]) / 2

    lon_edges[1:-1] = (lon[:-1] + lon[1:]) / 2
    lon_edges[0] = lon[0] - (lon[1] - lon[0]) / 2
    lon_edges[-1] = lon[-1] + (lon[-1] - lon[-2]) / 2

    # Convert to radians
    lat_edges_rad = np.deg2rad(lat_edges)
    lon_edges_rad = np.deg2rad(lon_edges)

    # ---- Pixel area calculation ----
    dlon = lon_edges_rad[1:] - lon_edges_rad[:-1]
    sin_dlat = np.sin(lat_edges_rad[1:]) - np.sin(lat_edges_rad[:-1])

    pixel_area = (
        R**2
        * sin_dlat[:, None]
        * dlon[None, :]
    )  # km^2

    # ---- Sum area for cluster pixels only ----
    area_km2 = pixel_area[mask].sum()

    return area_km2


# ------------------------------
# Example usage
# ------------------------------
for i, r in enumerate(top3, start=1):

    area_km2 = compute_cluster_area_km2(labeled_da, r)

    print(f"Cluster rank {i} (ID {r['cluster']}):")
    print(f"  Cluster size (pixels) = {r['size']}")
    print(f"  Pixel-based area = {area_km2:.2f} km²\n")


############# single color @@@@@@@
fig, ax = plt.subplots(figsize=(10, 7))

# Step 1: Show all hotspot cells in ONE color (e.g. red)
# instead of different colors per cluster
hotspot_display = xr.where(labeled_da > 0, 1, np.nan)
hotspot_display.plot(
    ax=ax,
    cmap="Reds",
    alpha=0.6,
    add_colorbar=False
)

# Step 2: Highlight ONLY top 3 clusters in distinct colors
top3_colors = {1: "gold", 2: "cyan", 3: "lime"}
for rank, r in enumerate(top3, start=1):
    cluster_mask = xr.where(labeled_da == r["cluster"], 1, np.nan)
    cluster_mask.plot(
        ax=ax,
        cmap=mcolors.ListedColormap([top3_colors[rank]]),
        alpha=0.8,
        add_colorbar=False
    )
    # Bounding box
    ax.plot(
        [r["lon_min"], r["lon_max"], r["lon_max"],
         r["lon_min"], r["lon_min"]],
        [r["lat_min"], r["lat_min"], r["lat_max"],
         r["lat_max"], r["lat_min"]],
        color=top3_colors[rank], linewidth=2
    )

# Step 3: Nepal boundary
nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1.2)

# Step 4: Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="red", alpha=0.6, label="All hotspot clusters"),
    Patch(facecolor="gold", label="Cluster 1 (largest)"),
    Patch(facecolor="cyan", label="Cluster 2"),
    Patch(facecolor="lime", label="Cluster 3"),
]
ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

ax.set_title("Wildfire Hotspot Clusters — Nepal", fontsize=10)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\Clusters\hotspot_clusters_clean.png",
            dpi=300, bbox_inches="tight")
plt.show()