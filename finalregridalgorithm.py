##################### WORKING + CF-1.10 COMPLIANT ############################
import xarray as xr
import pandas as pd
import numpy as np
import os
import re
from collections import defaultdict
from datetime import datetime

# ------------------------------------------------
# Directory containing VIIRS files
# ------------------------------------------------
data_dir = r"S:\viirs\VNP14IMG_002-20251229_070856"
out_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"
os.makedirs(out_dir, exist_ok=True)

# ------------------------------------------------
# Nepal bounding box
# ------------------------------------------------
lat_min, lat_max = 26.3, 30.5
lon_min, lon_max = 80.0, 88.5

# ------------------------------------------------
# Grid resolution (degrees)
# ------------------------------------------------
res = 0.02197265625  # ~10 km
lat_bins = np.arange(lat_min, lat_max + res, res)
lon_bins = np.arange(lon_min, lon_max + res, res)

lat_centers = (lat_bins[:-1] + lat_bins[1:]) / 2
lon_centers = (lon_bins[:-1] + lon_bins[1:]) / 2

# ------------------------------------------------
# Read all .nc files
# ------------------------------------------------
files = sorted(
    os.path.join(data_dir, f)
    for f in os.listdir(data_dir)
    if f.endswith(".nc")
)

# ------------------------------------------------
# Group files by day (Ayyyyddd)
# ------------------------------------------------
files_by_day = defaultdict(list)
for f in files:
    m = re.search(r"A(\d{7})", os.path.basename(f))
    if m:
        files_by_day[m.group(1)].append(f)

# ------------------------------------------------
# Loop day-wise
# ------------------------------------------------
for day, day_files in sorted(files_by_day.items()):

    daily_dfs = []
    obs_date = None

    # --------------------------------------------
    # Read all granules for the day
    # --------------------------------------------
    for file_path in day_files:
        ds = xr.open_dataset(file_path)

        fire = ds[
            ["FP_latitude", "FP_longitude", "FP_power",
             "FP_line", "FP_sample", "FP_day"]
        ]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        mask = ds["fire mask"].values
        df["mask"] = mask[df["FP_line"], df["FP_sample"]]

        df = df[df["mask"].isin([8, 9])]

        df = df[
            (df.FP_latitude >= lat_min)
            & (df.FP_latitude <= lat_max)
            & (df.FP_longitude >= lon_min)
            & (df.FP_longitude <= lon_max)
        ]

        if not df.empty:
            daily_dfs.append(df)

        if obs_date is None:
            obs_date = ds.attrs.get("RangeBeginningDate")

        ds.close()

    # --------------------------------------------
    # Create empty grid
    # --------------------------------------------
    nlat = len(lat_centers)
    nlon = len(lon_centers)

    fire_count = np.zeros((nlat, nlon), dtype=np.int32)
    frp_sum = np.zeros((nlat, nlon), dtype=np.float32)
    frp_max = np.full((nlat, nlon), np.nan, dtype=np.float32)
    day_count = np.zeros((nlat, nlon), dtype=np.int32)
    night_count = np.zeros((nlat, nlon), dtype=np.int32)
    day_night_mode = np.full((nlat, nlon), np.nan, dtype=np.float32)

    # --------------------------------------------
    # Bin fires
    # --------------------------------------------
    if daily_dfs:
        df_day = pd.concat(daily_dfs, ignore_index=True)

        df_day["ilat"] = np.digitize(df_day.FP_latitude, lat_bins) - 1
        df_day["ilon"] = np.digitize(df_day.FP_longitude, lon_bins) - 1

        for (i, j), group in df_day.groupby(["ilat", "ilon"]):
            if 0 <= i < nlat and 0 <= j < nlon:
                fire_count[i, j] = len(group)
                frp_sum[i, j] = group.FP_power.sum()
                frp_max[i, j] = group.FP_power.max()
                day_count[i, j] = (group.FP_day == 1).sum()
                night_count[i, j] = (group.FP_day == 0).sum()
                day_night_mode[i, j] = int(group.FP_day.mode()[0])

    # --------------------------------------------
    # Date fallback
    # --------------------------------------------
    if obs_date is None:
        obs_date = datetime.strptime(day[1:], "%Y%j")
    obs_date = pd.to_datetime(obs_date)

    # --------------------------------------------
    # Cell bounds (CF recommended)
    # --------------------------------------------
    lat_bnds = np.vstack([lat_bins[:-1], lat_bins[1:]]).T
    lon_bnds = np.vstack([lon_bins[:-1], lon_bins[1:]]).T

    # --------------------------------------------
    # Create Dataset
    # --------------------------------------------
    ds_out = xr.Dataset(
        data_vars=dict(
            fire_count=(["lat", "lon"], fire_count),
            frp_sum=(["lat", "lon"], frp_sum),
            frp_max=(["lat", "lon"], frp_max),
            day_count=(["lat", "lon"], day_count),
            night_count=(["lat", "lon"], night_count),
            day_night_mode=(["lat", "lon"], day_night_mode),
        ),
        coords=dict(
            lat=("lat", lat_centers),
            lon=("lon", lon_centers),
            time=("time", [obs_date]),
        ),
        attrs=dict(
            title="VIIRS Daily Fire Gridded Product (Nepal)",
            source="VNP14IMG",
            Conventions="CF-1.10",
            grid_resolution=f"{res} degree",
            spatial_extent="Nepal",
            filtering="fire mask values 8 and 9 only",
            geospatial_lat_min=lat_min,
            geospatial_lat_max=lat_max,
            geospatial_lon_min=lon_min,
            geospatial_lon_max=lon_max,
            geospatial_lat_units="degrees_north",
            geospatial_lon_units="degrees_east",
            time_coverage_start=str(obs_date),
            time_coverage_end=str(obs_date),
        ),
    )

    # --------------------------------------------
    # Coordinate attributes
    # --------------------------------------------
    ds_out["lat"].attrs = {
        "standard_name": "latitude",
        "long_name": "latitude",
        "units": "degrees_north",
        "axis": "Y",
        "bounds": "lat_bnds",
    }

    ds_out["lon"].attrs = {
        "standard_name": "longitude",
        "long_name": "longitude",
        "units": "degrees_east",
        "axis": "X",
        "bounds": "lon_bnds",
    }

    ds_out["time"].attrs = {
        "standard_name": "time",
        "long_name": "time of observation",
    }

    ds_out["lat_bnds"] = (("lat", "bnds"), lat_bnds)
    ds_out["lon_bnds"] = (("lon", "bnds"), lon_bnds)

    # --------------------------------------------
    # Variable attributes (NO _FillValue here!)
    # --------------------------------------------
    ds_out["fire_count"].attrs = {
        "long_name": "number of fire detections per grid cell",
        "units": "1",
    }

    ds_out["frp_sum"].attrs = {
        "long_name": "sum of fire radiative power",
        "units": "MW",
    }

    ds_out["frp_max"].attrs = {
        "long_name": "maximum fire radiative power",
        "units": "MW",
    }

    ds_out["day_count"].attrs = {
        "long_name": "number of daytime fire detections",
        "units": "1",
    }

    ds_out["night_count"].attrs = {
        "long_name": "number of nighttime fire detections",
        "units": "1",
    }

    ds_out["day_night_mode"].attrs = {
        "long_name": "dominant fire detection time (day=1, night=0)",
        "units": "1",
        "flag_values": [0, 1],
        "flag_meanings": "night day",
    }

    # --------------------------------------------
    # NetCDF encoding (ONLY place for _FillValue)
    # --------------------------------------------
    encoding = {
        "frp_max": {"_FillValue": np.nan},
        "day_night_mode": {"_FillValue": np.nan},
    }

    # --------------------------------------------
    # Save NetCDF
    # --------------------------------------------
    out_file = os.path.join(
        out_dir,
        f"VIIRS_FIRE_NEPAL_{obs_date.strftime('%Y%m%d')}.nc",
    )

    ds_out.to_netcdf(out_file, encoding=encoding)
    print(f"Saved: {out_file} | Fires: {fire_count.sum()}")


##################### WORKING ##############################################
import xarray as xr
import pandas as pd
import numpy as np
import os
import re
from collections import defaultdict
from datetime import datetime

# ------------------------------------------------
# Directory containing VIIRS files
# ------------------------------------------------
data_dir = r"S:\viirs\VNP14IMG_002-20251227_070636"
out_dir = r"S:\viirs\AAAP_MAY_VIIRS_daily_gridded_0.021_nc"
os.makedirs(out_dir, exist_ok=True)

# ------------------------------------------------
# Nepal bounding box
# ------------------------------------------------
lat_min, lat_max = 26.3, 30.5
lon_min, lon_max = 80.0, 88.5

# ------------------------------------------------
# Grid resolution (degrees)
# ------------------------------------------------
res = 0.02197265625  # ~10 km
lat_bins = np.arange(lat_min, lat_max + res, res)
lon_bins = np.arange(lon_min, lon_max + res, res)

lat_centers = (lat_bins[:-1] + lat_bins[1:]) / 2
lon_centers = (lon_bins[:-1] + lon_bins[1:]) / 2

# ------------------------------------------------
# Read all .nc files
# ------------------------------------------------
files = sorted(
    os.path.join(data_dir, f)
    for f in os.listdir(data_dir)
    if f.endswith(".nc")
)

# ------------------------------------------------
# Group files by day (Ayyyyddd)
# ------------------------------------------------
files_by_day = defaultdict(list)
for f in files:
    m = re.search(r"A(\d{7})", os.path.basename(f))
    if m:
        files_by_day[m.group(1)].append(f)

# ------------------------------------------------
# Loop day-wise
# ------------------------------------------------
for day, day_files in sorted(files_by_day.items()):

    daily_dfs = []
    obs_date = None

    # --------------------------------------------
    # Read all granules for the day
    # --------------------------------------------
    for file_path in day_files:
        ds = xr.open_dataset(file_path)

        # Extract fire pixel variables
        fire = ds[
            ["FP_latitude", "FP_longitude", "FP_power", "FP_line", "FP_sample", "FP_day"]
        ]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        # Fire mask array
        mask = ds["fire mask"].values
        df["mask"] = mask[df["FP_line"], df["FP_sample"]]

        # Apply only fire mask filter
        df = df[df["mask"].isin([8, 9])]

        # Nepal bounding box
        df = df[
            (df.FP_latitude >= lat_min)
            & (df.FP_latitude <= lat_max)
            & (df.FP_longitude >= lon_min)
            & (df.FP_longitude <= lon_max)
        ]

        if not df.empty:
            daily_dfs.append(df)

        if obs_date is None:
            obs_date = ds.attrs.get("RangeBeginningDate")

        ds.close()

    # --------------------------------------------
    # Create empty grid
    # --------------------------------------------
    nlat = len(lat_centers)
    nlon = len(lon_centers)

    fire_count = np.zeros((nlat, nlon), dtype=np.int32)
    frp_sum = np.zeros((nlat, nlon), dtype=np.float32)
    frp_max = np.full((nlat, nlon), np.nan, dtype=np.float32)
    day_count = np.zeros((nlat, nlon), dtype=np.int32)
    night_count = np.zeros((nlat, nlon), dtype=np.int32)
    day_night_mode = np.full((nlat, nlon), np.nan, dtype=np.float32)

    # --------------------------------------------
    # Bin fires if any exist
    # --------------------------------------------
    if daily_dfs:
        df_day = pd.concat(daily_dfs, ignore_index=True)

        # Assign grid cell indices
        df_day["ilat"] = np.digitize(df_day.FP_latitude, lat_bins) - 1
        df_day["ilon"] = np.digitize(df_day.FP_longitude, lon_bins) - 1

        # Group by grid cell
        for (i, j), group in df_day.groupby(["ilat", "ilon"]):
            if 0 <= i < nlat and 0 <= j < nlon:
                fire_count[i, j] = len(group)
                frp_sum[i, j] = group.FP_power.sum()
                frp_max[i, j] = group.FP_power.max()
                day_count[i, j] = (group.FP_day == 1).sum()
                night_count[i, j] = (group.FP_day == 0).sum()
                day_night_mode[i, j] = int(group.FP_day.mode()[0])

    # --------------------------------------------
    # Assign date for zero-fire days
    # --------------------------------------------
    if obs_date is None:
        obs_date = datetime.strptime(day[1:], "%Y%j")

    # --------------------------------------------
    # Create xarray Dataset
    # --------------------------------------------
    ds_out = xr.Dataset(
        data_vars=dict(
            fire_count=(["lat", "lon"], fire_count),
            frp_sum=(["lat", "lon"], frp_sum),
            frp_max=(["lat", "lon"], frp_max),
            day_count=(["lat", "lon"], day_count),
            night_count=(["lat", "lon"], night_count),
            day_night_mode=(["lat", "lon"], day_night_mode),
        ),
        coords=dict(
            lat=lat_centers,
            lon=lon_centers,
            time=pd.to_datetime(obs_date),
        ),
        attrs=dict(
            title="VIIRS Daily Fire Gridded Product (Nepal)",
            source="VNP14IMG",
            grid_resolution=f"{res} degree",
            spatial_extent="Nepal",
            filtering="fire mask 8/9 only",
        ),
    )

    # --------------------------------------------
    # Save NetCDF
    # --------------------------------------------
    out_file = os.path.join(
        out_dir,
        f"VIIRS_FIRE_NEPAL_{pd.to_datetime(obs_date).strftime('%Y%m%d')}.nc",
    )

    ds_out.to_netcdf(out_file)
    print(f"Saved: {out_file} | Fires: {fire_count.sum()}")





 ############## PREVIOUS ##############
import xarray as xr
import pandas as pd
import numpy as np
import os
import re
from collections import defaultdict
from datetime import datetime
from scipy.stats import mode

# ------------------------------------------------
# Directories
# ------------------------------------------------
data_dir = r"S:\viirs\test"
out_dir = r"S:\viirs\test_daily_gridded_0.021_nc"
os.makedirs(out_dir, exist_ok=True)

# ------------------------------------------------
# Nepal bounding box
# ------------------------------------------------
lat_min, lat_max = 26.3, 30.5
lon_min, lon_max = 80.0, 88.5

# ------------------------------------------------
# Grid resolution (degrees)
# ------------------------------------------------
res = 0.02197265625  # ~10 km
lat_bins = np.arange(lat_min, lat_max + res, res)
lon_bins = np.arange(lon_min, lon_max + res, res)

lat_centers = (lat_bins[:-1] + lat_bins[1:]) / 2
lon_centers = (lon_bins[:-1] + lon_bins[1:]) / 2

# ------------------------------------------------
# Read all .nc files
# ------------------------------------------------
files = sorted(
    os.path.join(data_dir, f)
    for f in os.listdir(data_dir)
    if f.endswith(".nc")
)

# ------------------------------------------------
# Group files by day (Ayyyyddd)
# ------------------------------------------------
files_by_day = defaultdict(list)
for f in files:
    m = re.search(r"A(\d{7})", os.path.basename(f))
    if m:
        files_by_day[m.group(1)].append(f)

# ------------------------------------------------
# Loop over days
# ------------------------------------------------
for day, day_files in sorted(files_by_day.items()):
    daily_dfs = []
    obs_date = None

    # --------------------------------------------
    # Read all granules for the day
    # --------------------------------------------
    for file_path in day_files:
        ds = xr.open_dataset(file_path)

        fire = ds[["FP_latitude", "FP_longitude", "FP_power", "FP_line", "FP_sample", "FP_day"]]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        # QA and fire mask
        qa = ds["algorithm QA"].values
        mask = ds["fire mask"].values
        df["qa"] = qa[df["FP_line"], df["FP_sample"]]
        df["mask"] = mask[df["FP_line"], df["FP_sample"]]

        # Filter for Nepal and fire mask 8/9
        df = df[df["mask"].isin([8, 9])]
        df = df[
            (df.FP_latitude >= lat_min)
            & (df.FP_latitude <= lat_max)
            & (df.FP_longitude >= lon_min)
            & (df.FP_longitude <= lon_max)
        ]

        if not df.empty:
            daily_dfs.append(df)

        if obs_date is None:
            obs_date = ds.attrs.get("RangeBeginningDate")

        ds.close()

    # --------------------------------------------
    # Create empty grid
    # --------------------------------------------
    nlat = len(lat_centers)
    nlon = len(lon_centers)

    fire_count = np.zeros((nlat, nlon), dtype=np.int32)
    frp_sum = np.zeros((nlat, nlon), dtype=np.float32)
    frp_max = np.full((nlat, nlon), np.nan, dtype=np.float32)
    day_count = np.zeros((nlat, nlon), dtype=np.int32)
    night_count = np.zeros((nlat, nlon), dtype=np.int32)
    day_night_mode = np.full((nlat, nlon), np.nan, dtype=np.float32)

    # --------------------------------------------
    # Aggregate fires per grid
    # --------------------------------------------
    if daily_dfs:
        df_day = pd.concat(daily_dfs, ignore_index=True)
        df_day["ilat"] = np.digitize(df_day.FP_latitude, lat_bins) - 1
        df_day["ilon"] = np.digitize(df_day.FP_longitude, lon_bins) - 1

        for (i, j), group in df_day.groupby(["ilat", "ilon"]):
            if 0 <= i < nlat and 0 <= j < nlon:
                fire_count[i, j] = len(group)
                frp_sum[i, j] = group["FP_power"].sum()
                frp_max[i, j] = group["FP_power"].max()
                day_count[i, j] = (group["FP_day"] == 1).sum()
                night_count[i, j] = (group["FP_day"] == 0).sum()
                day_night_mode[i, j] = int(mode(group["FP_day"], keepdims=False).mode[0])

    # --------------------------------------------
    # Assign date if missing
    # --------------------------------------------
    if obs_date is None:
        obs_date = datetime.strptime(day[1:], "%Y%j")

    # --------------------------------------------
    # Create xarray Dataset
    # --------------------------------------------
    ds_out = xr.Dataset(
        data_vars=dict(
            fire_count=(["lat", "lon"], fire_count),
            frp_sum=(["lat", "lon"], frp_sum),
            frp_max=(["lat", "lon"], frp_max),
            day_count=(["lat", "lon"], day_count),
            night_count=(["lat", "lon"], night_count),
            day_night_mode=(["lat", "lon"], day_night_mode),
        ),
        coords=dict(
            lat=lat_centers,
            lon=lon_centers,
            time=pd.to_datetime(obs_date),
        ),
        attrs=dict(
            title="VIIRS Daily Fire Gridded Product (Nepal)",
            source="VNP14IMG",
            grid_resolution=f"{res} degree",
            spatial_extent="Nepal",
            filtering="QA bits 0–6 = 0, not over water, fire mask 8/9",
        ),
    )

    # --------------------------------------------
    # Save NetCDF with compression
    # --------------------------------------------
    encoding = {var: {"zlib": True, "complevel": 4} for var in ds_out.data_vars}
    out_file = os.path.join(
        out_dir,
        f"VIIRS_FIRE_NEPAL_{pd.to_datetime(obs_date).strftime('%Y%m%d')}.nc",
    )
    ds_out.to_netcdf(out_file, encoding=encoding)

    print(f"Saved: {out_file} | Fires: {fire_count.sum()}")



#####################
import xarray as xr
import matplotlib.pyplot as plt

# Load dataset
data_file = r"S:\viirs\AAP_MAY_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210401.nc"
ds = xr.open_dataset(data_file)

# Extract variables
fire_count = ds["fire_count"]
day_count = ds["day_count"]
night_count = ds["night_count"]

# Print total number of fires
print(f"Total fires: {int(fire_count.sum().values)}")
print(f"Total day fires: {int(day_count.sum().values)}")
print(f"Total night fires: {int(night_count.sum().values)}")

# Plotting
fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)

# Fire count (total)
im0 = axes[0].pcolormesh(ds["lon"], ds["lat"], fire_count, shading='auto', cmap='hot')
axes[0].set_title("Total Fires Count")
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")
fig.colorbar(im0, ax=axes[0], label="Number of Fires")

# Day count
im1 = axes[1].pcolormesh(ds["lon"], ds["lat"], day_count, shading='auto', cmap='Reds')
axes[1].set_title("Day Fires Count")
axes[1].set_xlabel("Longitude")
axes[1].set_ylabel("Latitude")
fig.colorbar(im1, ax=axes[1], label="Number of Fires")

# Night count
im2 = axes[2].pcolormesh(ds["lon"], ds["lat"], night_count, shading='auto', cmap='Blues')
axes[2].set_title("Night Fires Count")
axes[2].set_xlabel("Longitude")
axes[2].set_ylabel("Latitude")
fig.colorbar(im2, ax=axes[2], label="Number of Fires")

plt.suptitle(f"VIIRS Fires in Nepal on {str(ds.time.values)[:10]}", fontsize=16)
plt.show()



###############






######################################

