import xarray as xr
import pandas as pd
import numpy as np
import os
import re
from collections import defaultdict
from datetime import datetime

# ------------------------------------------------
# Directories
# ------------------------------------------------
data_dir = r"S:\viirs\VNP14IMG_002-20260104_142438"
out_dir = r"S:\viirs\gridalligned_2024_VIIRS_daily_gridded_0.021_nc"
os.makedirs(out_dir, exist_ok=True)

# ------------------------------------------------
# Nepal bounding box
# ------------------------------------------------
lat_min, lat_max = 26.3, 30.5
lon_min, lon_max = 80.0, 88.5

# ------------------------------------------------
# Load a TROPOMI file to get grid
# ------------------------------------------------
tropomi_path = r"C:\Users\ACER\Downloads\April1_s5p-no2-cropped.nc"
tr = xr.open_dataset(tropomi_path)

# TROPOMI grid
lat_centers = tr.latitude.values
lon_centers = tr.longitude.values
res_lat = float(lat_centers[1] - lat_centers[0])
res_lon = float(lon_centers[1] - lon_centers[0])

# CF-compliant cell bounds
lat_bins = np.concatenate([lat_centers - res_lat / 2, [lat_centers[-1] + res_lat / 2]])
lon_bins = np.concatenate([lon_centers - res_lon / 2, [lon_centers[-1] + res_lon / 2]])

nlat = len(lat_centers)
nlon = len(lon_centers)

# ------------------------------------------------
# Read all .nc VIIRS files
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

        fire = ds[["FP_latitude", "FP_longitude", "FP_power",
                   "FP_line", "FP_sample", "FP_day"]]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        mask = ds["fire mask"].values
        df["mask"] = mask[df["FP_line"], df["FP_sample"]]
        df = df[df["mask"].isin([8, 9])]

        # Clip to Nepal bounding box
        df = df[
            (df.FP_latitude >= lat_min) & (df.FP_latitude <= lat_max) &
            (df.FP_longitude >= lon_min) & (df.FP_longitude <= lon_max)
        ]

        if not df.empty:
            daily_dfs.append(df)

        if obs_date is None:
            obs_date = ds.attrs.get("RangeBeginningDate")

        ds.close()

    # --------------------------------------------
    # Create empty arrays for fire metrics
    # --------------------------------------------
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
    # Cell bounds
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
            grid_resolution=f"{res_lat} degree",
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
    # Variable attributes
    # --------------------------------------------
    ds_out["fire_count"].attrs = {"long_name": "number of fire detections per grid cell", "units": "1"}
    ds_out["frp_sum"].attrs = {"long_name": "sum of fire radiative power", "units": "MW"}
    ds_out["frp_max"].attrs = {"long_name": "maximum fire radiative power", "units": "MW"}
    ds_out["day_count"].attrs = {"long_name": "number of daytime fire detections", "units": "1"}
    ds_out["night_count"].attrs = {"long_name": "number of nighttime fire detections", "units": "1"}
    ds_out["day_night_mode"].attrs = {
        "long_name": "dominant fire detection time (day=1, night=0)",
        "units": "1",
        "flag_values": [0, 1],
        "flag_meanings": "night day",
    }

    # --------------------------------------------
    # NetCDF encoding
    # --------------------------------------------
    encoding = {"frp_max": {"_FillValue": np.nan}, "day_night_mode": {"_FillValue": np.nan}}

    # --------------------------------------------
    # Save NetCDF
    # --------------------------------------------
    out_file = os.path.join(out_dir, f"VIIRS_FIRE_NEPAL_{obs_date.strftime('%Y%m%d')}.nc")
    ds_out.to_netcdf(out_file, encoding=encoding)
    print(f"Saved: {out_file} | Total fires: {fire_count.sum()}")
