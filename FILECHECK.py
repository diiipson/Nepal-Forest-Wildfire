import xarray as xr
filepath=r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0606.002.2024073082629.nc"
check=xr.open_dataset(filepath)
check.info()
#############

import xarray as xr
import glob
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==================================================
# 1. Paths
# ==================================================
# no2_dir = r"S:\viirs\2024_tropomi_NO2"
no2_dir = r"S:\viirs\2024_tropomi_COT"
fire_dir = r"S:\viirs\gridalligned_2024_VIIRS_daily_gridded_0.021_nc"

no2_files = sorted(glob.glob(os.path.join(no2_dir, "*.nc")))
fire_files = sorted(glob.glob(os.path.join(fire_dir, "*.nc")))

if not no2_files or not fire_files:
    raise FileNotFoundError("NO2 or Fire files not found")

# ==================================================
# 2. Cluster bounding box (example: Cluster rank 3)
# ==================================================
lat_min, lat_max = 27.674560546875, 28.773193359375
lon_min, lon_max = 81.265869140625, 82.760009765625
# lat_min, lat_max = 27.80, 28.05
# lon_min, lon_max = 86.80, 87.15
# lat_min, lat_max = 28.7, 29.5
# lon_min, lon_max = 83.3, 84.2
# lat_min = 27.8
# lat_max = 28.5
# lon_min = 87.0
# lon_max = 87.8
# ==================================================
# 3. Initialize storage
# ==================================================
dates = []
no2_avg_list = []
fire_count_list = []

# ==================================================
# 4. Loop through daily files
# ==================================================
for no2_f, fire_f in zip(no2_files, fire_files):

    # ---------- NO2 ----------
    ds_no2 = xr.open_dataset(no2_f)

    date = pd.to_datetime(ds_no2["datetime_start"].values[0])

    # no2_region = ds_no2["tropospheric_NO2_column_number_density"].sel(
    no2_region = ds_no2["CO_column_number_density"].sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )

    no2_avg = no2_region.mean(
        dim=["latitude", "longitude"],
        skipna=True
    ).item()

    ds_no2.close()

    # ---------- FIRE COUNT ----------
    ds_fire = xr.open_dataset(fire_f)

    fire_region = ds_fire["fire_count"].sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max)
    )

    fire_sum = fire_region.sum(
        dim=["lat", "lon"],
        skipna=True
    ).item()

    ds_fire.close()

    # ---------- Save ----------
    dates.append(date)
    no2_avg_list.append(no2_avg)
    fire_count_list.append(fire_sum)

# ==================================================
# 5. Create DataFrame
# ==================================================
df = pd.DataFrame({
    "date": dates,
    "NO2_avg": no2_avg_list,
    "fire_count": fire_count_list
})

df.set_index("date", inplace=True)
df = df.dropna()

# ==================================================
# 6. Plot NO2 + Fire Count (Dual Axis)
# ==================================================
fig, ax1 = plt.subplots(figsize=(14, 5))

# NO2 (left axis)
ax1.plot(
    df.index,
    df["NO2_avg"],
    color="darkgreen",
    linewidth=1.5
)
ax1.set_xlabel("Date")
ax1.set_ylabel("Tropospheric NO₂ (µmol/m²)", color="darkgreen")
ax1.tick_params(axis="y", labelcolor="darkgreen")

# Fire count (right axis)
ax2 = ax1.twinx()
ax2.plot(
    df.index,
    df["fire_count"],
    color="firebrick",
    linewidth=1.3,
    alpha=0.7
)
ax2.set_ylabel("Fire Count", color="firebrick")
ax2.tick_params(axis="y", labelcolor="firebrick")

# Layout
ax1.grid(alpha=0.3)
plt.title("Daily NO₂ and Fire Count Time Series (Cluster Region)")
plt.tight_layout()
plt.show()

# ==================================================
# 6. Filter for January to June
# ==================================================
df_plot = df[df.index.month.isin([1, 2, 3, 4, 5, 6])]

# ==================================================
# 7. Plot NO2 + Fire Count (Dual Axis)
# ==================================================
fig, ax1 = plt.subplots(figsize=(5, 3))

# --- Prepare x-axis: one tick per month ---
# Get unique months and their first occurrence
month_starts = df_plot.index.to_series().groupby(df_plot.index.month).first()
month_numbers = month_starts.index  # 1,2,3,4,5,6,7

# NO2 (left axis)
ax1.plot(
    df_plot.index,
    df_plot["NO2_avg"],
    color="black",
    linewidth=1.5
)
ax1.set_xlabel("Month")
# ax1.set_ylabel("Tropospheric NO₂ (µmol/m²)", color="darkgreen")
ax1.set_ylabel("Total CO (mmol/m²)", color="black")
ax1.tick_params(axis="y", labelcolor="black")

# Fire count (right axis)
ax2 = ax1.twinx()
ax2.plot(
    df_plot.index,
    df_plot["fire_count"],
    color="firebrick",
    linewidth=1.3,
    alpha=0.7
)
ax2.set_ylabel("Fire Count", color="firebrick")
ax2.tick_params(axis="y", labelcolor="firebrick")

# --- Set x-ticks at first day of each month ---
ax1.set_xticks(month_starts.values)
ax1.set_xticklabels(month_numbers)

# Layout
ax1.grid(alpha=0.3)
plt.tight_layout()

# # Save figure
# plt.savefig(
#      r"S:\viirs\pictures\COT\2024_cluster3.png",
#      dpi=1000,
#      bbox_inches="tight"
# )
plt.show()



###################
import xarray as xr
import glob
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==================================================
# 1. File paths
# ==================================================
data_dir = r"S:\viirs\tropomi1\Nepal"
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

if not files:
    raise FileNotFoundError("No NetCDF files found!")

# ==================================================
# 2. Coordinate of interest
# ==================================================
lat_point = 29.2  # example latitude
lon_point = 85.5  # example longitude

# ==================================================
# 3. Initialize lists for time series
# ==================================================
dates = []
no2_values = []

# ==================================================
# 4. Loop through all daily files
# ==================================================
for f in files:
    ds = xr.open_dataset(f)

    # Extract NO2 at nearest grid cell
    # no2_at_point = ds["tropospheric_NO2_column_number_density"].sel(
    no2_at_point = ds["CO_column_number_density"].sel(
        latitude=lat_point,
        longitude=lon_point,
        method="nearest"
    ).values

    # Extract the date
    date = pd.to_datetime(ds["datetime_start"].values[0])

    dates.append(date)

    # Ensure the value is a float (flatten if needed)
    if no2_at_point.size == 1:
        no2_values.append(float(no2_at_point))
    else:
        no2_values.append(float(no2_at_point.flatten()[0]))

    ds.close()

# ==================================================
# 5. Create pandas DataFrame
# ==================================================
df_no2 = pd.DataFrame({
    "date": pd.to_datetime(dates),
    "NO2_umol_m2": no2_values
})

df_no2.set_index("date", inplace=True)

# Drop missing values (NaNs) to avoid plotting issues
df_no2 = df_no2.dropna()

# ==================================================
# 6. Convert to proper 1D arrays for plotting
# ==================================================
x = df_no2.index.to_numpy().flatten()
y = df_no2["NO2_umol_m2"].to_numpy().flatten()

# ==================================================
# 7. Plot the daily NO2 time series
# ==================================================
plt.figure(figsize=(14, 5))
plt.plot(x, y, color="darkblue", linewidth=1)
plt.xlabel("Date")
plt.ylabel("Tropospheric NO2 (µmol/m²)")
plt.title(f"Daily NO2 Time Series at Lat {lat_point}, Lon {lon_point}")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()




#############################
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
import glob
import os
import pandas as pd

# ==================================================
# 1. File paths
# ==================================================
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

if not files:
    raise FileNotFoundError("No NetCDF files found!")

# ==================================================
# 2. Initialize accumulators for annual aggregation
# ==================================================
fire_annual = None
frp_annual = None

# Also initialize for daily totals
dates = []
daily_fire_counts = []

# ==================================================
# 3. Loop through daily files
# ==================================================
for f in files:
    ds = xr.open_dataset(f)

    # Sum into annual map
    if fire_annual is None:
        fire_annual = ds["fire_count"].copy(deep=True)
        frp_annual = ds["frp_sum"].copy(deep=True)
    else:
        fire_annual += ds["fire_count"]
        frp_annual += ds["frp_sum"]

    # Daily total for time series
    total_fire = ds["fire_count"].sum(dim=["lat", "lon"]).item()
    date = pd.to_datetime(ds["time"].values[0])
    dates.append(date)
    daily_fire_counts.append(total_fire)

    ds.close()

print("Annual aggregation completed")

# ==================================================
# 4. Percentile-based hotspot thresholds
# ==================================================
fire_thresh = fire_annual.quantile(0.95)
frp_thresh = frp_annual.quantile(0.95)

# ==================================================
# 5. Hotspot mask
# ==================================================
hotspot = (fire_annual >= fire_thresh) | (frp_annual >= frp_thresh)

# ==================================================
# 6. Detect contiguous hotspot clusters
# ==================================================
labeled, n_clusters = label(hotspot.values)
print(f"Detected {n_clusters} hotspot regions")

# ==================================================
# 7. Extract bounding boxes and cluster sizes
# ==================================================
regions = []
for i in range(1, n_clusters + 1):
    mask = labeled == i
    lat_idxs, lon_idxs = np.where(mask)
    
    lat_min = hotspot['lat'].values[lat_idxs].min()
    lat_max = hotspot['lat'].values[lat_idxs].max()
    lon_min = hotspot['lon'].values[lon_idxs].min()
    lon_max = hotspot['lon'].values[lon_idxs].max()
    
    regions.append({
        'cluster': i,
        'lat_min': lat_min,
        'lat_max': lat_max,
        'lon_min': lon_min,
        'lon_max': lon_max,
        'size': mask.sum()  # number of pixels
    })

# ==================================================
# 8. Select top 3 hotspot regions by size
# ==================================================
regions_sorted = sorted(regions, key=lambda x: x['size'], reverse=True)
top3_regions = regions_sorted[:3]

# Print top 3 regions
for r in top3_regions:
    print(f"Region {r['cluster']}: lat {r['lat_min']:.2f}-{r['lat_max']:.2f}, "
          f"lon {r['lon_min']:.2f}-{r['lon_max']:.2f}, size {r['size']} pixels")

# ==================================================
# 9. Plot annual fire count with top 3 hotspots
# ==================================================
plt.figure(figsize=(10, 8))
fire_annual.plot(cmap="Greys", alpha=0.5, cbar_kwargs={"label": "Annual Fire Count"})
hotspot.plot(cmap="Reds", alpha=0.6, add_colorbar=False)

# Draw bounding boxes for top 3 regions only
for r in top3_regions:
    plt.plot(
        [r['lon_min'], r['lon_max'], r['lon_max'], r['lon_min'], r['lon_min']],
        [r['lat_min'], r['lat_min'], r['lat_max'], r['lat_max'], r['lat_min']],
        color='blue', linewidth=2
    )

plt.title("Top 3 VIIRS Fire Hotspot Regions (Nepal 2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 10. Plot daily total fire count time series
# ==================================================
plt.figure(figsize=(14, 6))
plt.plot(dates, daily_fire_counts, color="firebrick", linewidth=1)
plt.xlabel("Date")
plt.ylabel("Total Fire Count")
plt.title("Daily VIIRS Fire Count in Nepal (2021)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()



###########################
import xarray as xr
import matplotlib.pyplot as plt
import glob
import os
import pandas as pd

# Folder containing all 2021 daily files
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"

# Get all NetCDF files (sorted by date)
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

dates = []
daily_fire_counts = []

for f in files:
    ds = xr.open_dataset(f)

    # Sum fire_count over space (lat, lon)
    total_fire = ds["fire_count"].sum(dim=["lat", "lon"]).item()

    # Extract date as pandas datetime
    date = pd.to_datetime(ds["time"].values[0])

    dates.append(date)
    daily_fire_counts.append(total_fire)

    ds.close()

# Plot
plt.figure(figsize=(14, 6))
plt.plot(dates, daily_fire_counts, color="firebrick", linewidth=1)
plt.xlabel("Date")
plt.ylabel("Total Fire Count")
plt.title("Daily VIIRS Fire Count in Nepal (2021)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
import xarray as xr import matplotlib.pyplot as plt import numpy as np from scipy.ndimage import label # Assume hotspot is your boolean xarray.DataArray (from previous code) # -------------------------------------------------- # 1. Label contiguous hotspot clusters # -------------------------------------------------- labeled, n_clusters = label(hotspot.values) print(f"Detected {n_clusters} hotspot regions") # -------------------------------------------------- # 2. Extract bounding boxes for each region # -------------------------------------------------- regions = [] for i in range(1, n_clusters+1): mask = labeled == i lat_idxs, lon_idxs = np.where(mask) lat_min = hotspot['lat'].values[lat_idxs].min() lat_max = hotspot['lat'].values[lat_idxs].max() lon_min = hotspot['lon'].values[lon_idxs].min() lon_max = hotspot['lon'].values[lon_idxs].max() regions.append({ 'cluster': i, 'lat_min': lat_min, 'lat_max': lat_max, 'lon_min': lon_min, 'lon_max': lon_max }) # Print detected regions for r in regions: print(f"Region {r['cluster']}: lat {r['lat_min']:.2f}-{r['lat_max']:.2f}, " f"lon {r['lon_min']:.2f}-{r['lon_max']:.2f}") # -------------------------------------------------- # 3. Plot each hotspot region # -------------------------------------------------- plt.figure(figsize=(10, 8)) fire_annual.plot(cmap="Greys", alpha=0.5, cbar_kwargs={"label": "Annual Fire Count"}) hotspot.plot(cmap="Reds", alpha=0.6, add_colorbar=False) # Plot bounding boxes around each hotspot region for r in regions: plt.plot([r['lon_min'], r['lon_max'], r['lon_max'], r['lon_min'], r['lon_min']], [r['lat_min'], r['lat_min'], r['lat_max'], r['lat_max'], r['lat_min']], color='blue', linewidth=2) plt.title("VIIRS Fire Hotspots with Bounding Boxes (Nepal 2021)") plt.xlabel("Longitude") plt.ylabel("Latitude") plt.tight_layout() plt.show()


##################
import xarray as xr
import matplotlib.pyplot as plt
import glob
import os

# Folder containing all 2021 daily files
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

# Initialize a variable to store the cumulative fire counts
total_fire_map = None

for f in files:
    ds = xr.open_dataset(f)
    
    # Initialize total_fire_map with the first file
    if total_fire_map is None:
        total_fire_map = ds["fire_count"].copy()
    else:
        total_fire_map += ds["fire_count"]
    
    ds.close()

# Plot the aggregated annual fire count map
plt.figure(figsize=(10, 8))
total_fire_map.plot(cmap="hot", cbar_kwargs={"label": "Annual Fire Count"})
plt.title("Total VIIRS Fire Count in Nepal (2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()


######### compare ########
import xarray as xr
import matplotlib.pyplot as plt

# File paths
file1 = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210101.nc"
file2 = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210401.nc"  # assuming second file is different

# Open datasets
ds1 = xr.open_dataset(file1)
ds2 = xr.open_dataset(file2)

# Variables to compare
variables = ['fire_count', 'frp_max', 'frp_sum']

# Plot comparison
fig, axes = plt.subplots(len(variables), 2, figsize=(12, 12))

for i, var in enumerate(variables):
    # Plot file 1
    ds1[var].plot(ax=axes[i, 0], cmap='hot')
    axes[i, 0].set_title(f"{var} - File 1")
    
    # Plot file 2
    ds2[var].plot(ax=axes[i, 1], cmap='hot')
    axes[i, 1].set_title(f"{var} - File 2")

plt.tight_layout()
plt.show()

ds2.info

for var in ds2.data_vars:
    print(f"\nVariable: {var}")
    print(ds2[var])


################## CCL ########
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
import glob
import os
import pandas as pd

# ==================================================
# 1. File paths
# ==================================================
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

if not files:
    raise FileNotFoundError("No NetCDF files found!")

# ==================================================
# 2. Initialize accumulators for annual aggregation
# ==================================================
fire_annual = None
frp_annual = None
dates = []
daily_fire_counts = []

# ==================================================
# 3. Loop through daily files
# ==================================================
# 3. Loop through daily files
# ==================================================
for f in files:
    ds = xr.open_dataset(f)
    
    # Get the date of this file
    date = pd.to_datetime(ds["time"].values[0])

    # Only include pre-monsoon months: March (3), April (4), May (5)
    if date.month in [3, 4, 5]:
        # Aggregate seasonal fire count and FRP
        if fire_annual is None:
            fire_annual = ds["fire_count"].copy(deep=True)
            frp_annual = ds["frp_sum"].copy(deep=True)
        else:
            fire_annual += ds["fire_count"]
            frp_annual += ds["frp_sum"]

        # Daily total for time series
        total_fire = ds["fire_count"].sum(dim=["lat", "lon"]).item()
        dates.append(date)
        daily_fire_counts.append(total_fire)

    ds.close()

print("Pre-monsoon (March–May) aggregation completed")


# ==================================================
# 4. Percentile-based hotspot thresholds
# ==================================================
fire_thresh = fire_annual.quantile(0.95)
frp_thresh = frp_annual.quantile(0.95)

# ==================================================
# 5. Hotspot mask
# ==================================================
hotspot = (fire_annual >= fire_thresh) | (frp_annual >= frp_thresh)

# ==================================================
# 6. Detect contiguous hotspot clusters
# ==================================================
# ==================================================
# 6. Detect contiguous hotspot clusters
# ==================================================
structure = np.array([[1, 1, 1],
                      [1, 1, 1],
                      [1, 1, 1]])
labeled, n_clusters = label(hotspot.values)

# labeled, n_clusters = label(hotspot.values)
print(f"Detected {n_clusters} hotspot regions")

# Convert to xarray
labeled_da = xr.DataArray(
    labeled,
    coords=hotspot.coords,
    dims=hotspot.dims,
    name="hotspot_clusters"
)

# ------------------- ADD HERE -------------------
# Clean cluster figure with white background for non-hotspot pixels
import matplotlib
cmap = matplotlib.cm.get_cmap("tab20").copy()
cmap.set_under("white")
plt.figure(figsize=(10, 8))
labeled_da.plot(cmap=cmap, vmin=1, add_colorbar=True, cbar_kwargs={"label": "Cluster ID"})
plt.title("Connected-Component Labeled Hotspot Clusters (VIIRS 2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()
# ------------------- END ADD -------------------

# ==================================================
# 7. Extract bounding boxes and cluster sizes
# ==================================================
regions = []
for i in range(1, n_clusters + 1):
    mask = labeled == i
    lat_idxs, lon_idxs = np.where(mask)
    
    lat_min = hotspot['lat'].values[lat_idxs].min()
    lat_max = hotspot['lat'].values[lat_idxs].max()
    lon_min = hotspot['lon'].values[lon_idxs].min()
    lon_max = hotspot['lon'].values[lon_idxs].max()
    
    regions.append({
        'cluster': i,
        'lat_min': lat_min,
        'lat_max': lat_max,
        'lon_min': lon_min,
        'lon_max': lon_max,
        'size': mask.sum()
    })

# ==================================================
# 8. Select top 3 hotspot regions by size
# ==================================================
regions_sorted = sorted(regions, key=lambda x: x['size'], reverse=True)
top3_regions = regions_sorted[:3]

for r in top3_regions:
    print(f"Region {r['cluster']}: lat {r['lat_min']:.2f}-{r['lat_max']:.2f}, "
          f"lon {r['lon_min']:.2f}-{r['lon_max']:.2f}, size {r['size']} pixels")
# ==================================================
# 8a. Diagnostic plot: mask of largest (Rank-1) cluster
# ==================================================
largest_cluster_id = top3_regions[0]['cluster']

pink_mask = labeled_da == largest_cluster_id

plt.figure(figsize=(6, 6))
pink_mask.plot(cmap="gray")
plt.title("Mask of Largest Contiguous Cluster (Rank 1)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()


# ==================================================
# 9. Plot annual fire count with top 3 hotspots
# ==================================================
plt.figure(figsize=(10, 8))
fire_annual.plot(cmap="Greys", alpha=0.5, cbar_kwargs={"label": "Annual Fire Count"})
hotspot.plot(cmap="Reds", alpha=0.6, add_colorbar=False)

# Draw bounding boxes for top 3 clusters
for r in top3_regions:
    plt.plot(
        [r['lon_min'], r['lon_max'], r['lon_max'], r['lon_min'], r['lon_min']],
        [r['lat_min'], r['lat_min'], r['lat_max'], r['lat_max'], r['lat_min']],
        color='blue', linewidth=2
    )

plt.title("Top 3 VIIRS Fire Hotspot Regions (Nepal 2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 10. Plot daily total fire count time series
# ==================================================
plt.figure(figsize=(14, 6))
plt.plot(dates, daily_fire_counts, color="firebrick", linewidth=1)
plt.xlabel("Date")
plt.ylabel("Total Fire Count")
plt.title("Daily VIIRS Fire Count in Nepal (2021)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# ==================================================
# 11. Plot labeled connected-component clusters as grid
# ==================================================
plt.figure(figsize=(10, 8))
labeled_da.plot(
    cmap="tab20",
    add_colorbar=True,
    cbar_kwargs={"label": "Cluster ID"}
)
plt.title("Connected-Component Labeled Hotspot Clusters (VIIRS 2021)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()

# ==================================================
# 12. Zoom to largest cluster for paper-quality figure
# ==================================================
# ==================================================
# 12. Zoomed view of all top 3 hotspot clusters
#     (colorful background, same style as Rank-1 plot)
# ==================================================
for idx, region in enumerate(top3_regions, start=1):

    zoomed = labeled_da.sel(
        lat=slice(region['lat_min'], region['lat_max']),
        lon=slice(region['lon_min'], region['lon_max'])
    )

    plt.figure(figsize=(6, 6))
    zoomed.plot(
        cmap="tab20",
        add_colorbar=False
    )

    # Optional: overlay grid lines to show individual pixels
    plt.gca().set_xticks(zoomed.lon.values, minor=True)
    plt.gca().set_yticks(zoomed.lat.values, minor=True)
    plt.grid(which="minor", color="black", linewidth=0.3)

    plt.title(f"Zoomed View of Hotspot Cluster Rank {idx}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()





# ==================================================
# 12. Zoomed view of all top 3 hotspot clusters
# ==================================================
for idx, region in enumerate(top3_regions, start=1):

    cluster_id = region['cluster']

    # Extract only this cluster
    cluster_da = labeled_da.where(labeled_da == cluster_id)

    # Zoom to bounding box
    zoomed = cluster_da.sel(
        lat=slice(region['lat_min'], region['lat_max']),
        lon=slice(region['lon_min'], region['lon_max'])
    )

    plt.figure(figsize=(6, 6))
    zoomed.plot(
        cmap="tab20",
        add_colorbar=False
    )

    # Optional: show grid cells
    plt.gca().set_xticks(zoomed.lon.values, minor=True)
    plt.gca().set_yticks(zoomed.lat.values, minor=True)
    plt.grid(which="minor", color="black", linewidth=0.3)

    plt.title(f"Zoomed View of Hotspot Cluster Rank {idx} (ID {cluster_id})")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()



import numpy as np
import matplotlib.pyplot as plt

# --------------------------
# Flatten and filter data
# --------------------------
fire_values = fire_annual.values.flatten()  # Pre-monsoon aggregated fire count
frp_values = frp_annual.values.flatten()    # Pre-monsoon aggregated FRP

# Remove zero values (optional, focus on active fire pixels)
fire_values = fire_values[fire_values > 0]
frp_values = frp_values[frp_values > 0]

# --------------------------
# Compute percentiles
# --------------------------
percentiles = np.arange(0, 101, 1)  # 0th to 100th percentile

fire_percentiles = np.percentile(fire_values, percentiles)
frp_percentiles = np.percentile(frp_values, percentiles)

# Compute 95th percentile thresholds
fire_thresh_95 = np.percentile(fire_values, 95)
frp_thresh_95 = np.percentile(frp_values, 95)

# --------------------------
# Plot Fire Count Percentiles
# --------------------------
plt.figure(figsize=(10,5))
plt.plot(percentiles, fire_percentiles, color='firebrick', linewidth=2, label='Fire Count')
plt.axhline(fire_thresh_95, color='blue', linestyle='--', label='95th percentile threshold')
plt.xlabel('Percentile')
plt.ylabel('Aggregated Fire Count (March–May)')
plt.title('Fire Count Percentile Distribution (Pre-monsoon)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# --------------------------
# Plot FRP Percentiles
# --------------------------
plt.figure(figsize=(10,5))
plt.plot(percentiles, frp_percentiles, color='orange', linewidth=2, label='FRP')
plt.axhline(frp_thresh_95, color='blue', linestyle='--', label='95th percentile threshold')
plt.xlabel('Percentile')
plt.ylabel('Aggregated FRP (MW)')
plt.title('FRP Percentile Distribution (Pre-monsoon)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# --------------------------
# Optional: Combined Plot
# --------------------------
plt.figure(figsize=(10,5))
plt.plot(percentiles, fire_percentiles, color='firebrick', linewidth=2, label='Fire Count')
plt.plot(percentiles, frp_percentiles, color='orange', linewidth=2, label='FRP')
plt.axhline(fire_thresh_95, color='red', linestyle='--', label='Fire Count 95th pct')
plt.axhline(frp_thresh_95, color='blue', linestyle='--', label='FRP 95th pct')
plt.xlabel('Percentile')
plt.ylabel('Aggregated Value (March–May)')
plt.title('Pre-monsoon Fire Count and FRP Percentile Distribution')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
