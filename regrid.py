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
out_dir = r"S:\viirs\AAP_MAY_VIIRS_daily_gridded_0.021_nc"
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
            [
                "FP_latitude",
                "FP_longitude",
                "FP_power",
                "FP_line",
                "FP_sample",
            ]
        ]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        # QA and fire mask arrays
        qa = ds["algorithm QA"].values
        mask = ds["fire mask"].values

        df["qa"] = qa[df["FP_line"], df["FP_sample"]]
        df["mask"] = mask[df["FP_line"], df["FP_sample"]]

        # Apply QA + fire mask filters
        qa_vals = df["qa"].to_numpy()
        df = df[
            ((qa_vals & 0b1111111) == 0)
            & (((qa_vals >> 19) & 1) == 0)
            & (df["mask"].isin([8, 9]))
        ]


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
    # Create empty grid (always)
    # --------------------------------------------
    nlat = len(lat_centers)
    nlon = len(lon_centers)

    fire_count = np.zeros((nlat, nlon), dtype=np.int32)
    frp_sum = np.zeros((nlat, nlon), dtype=np.float32)
    frp_max = np.full((nlat, nlon), np.nan, dtype=np.float32)

    # --------------------------------------------
    # Bin fires if any exist
    # --------------------------------------------
    if daily_dfs:
        df_day = pd.concat(daily_dfs, ignore_index=True)

        df_day["ilat"] = np.digitize(df_day.FP_latitude, lat_bins) - 1
        df_day["ilon"] = np.digitize(df_day.FP_longitude, lon_bins) - 1

        for _, r in df_day.iterrows():
            i, j = int(r.ilat), int(r.ilon)
            if 0 <= i < nlat and 0 <= j < nlon:
                fire_count[i, j] += 1
                frp_sum[i, j] += r.FP_power
                frp_max[i, j] = np.nanmax([frp_max[i, j], r.FP_power])

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
    # Save NetCDF
    # --------------------------------------------
    out_file = os.path.join(
        out_dir,
        f"VIIRS_FIRE_NEPAL_{pd.to_datetime(obs_date).strftime('%Y%m%d')}.nc",
    )

    ds_out.to_netcdf(out_file)
    print(f"Saved: {out_file} | Fires: {fire_count.sum()}")



import xarray as xr
import matplotlib.pyplot as plt

# -------------------------------
# Load daily gridded dataset
# -------------------------------
data = r"S:\viirs\AP_MAY_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210405.nc"
ds = xr.open_dataset(data)

# -------------------------------
# Extract variables
# -------------------------------
fire_count = ds['fire_count']
frp_sum = ds['frp_sum']
lat = ds['lat']
lon = ds['lon']

lat_res = (lat[1] - lat[0]).item()  # difference between consecutive lat points
lon_res = (lon[1] - lon[0]).item() # difference between consecutive lon points

print(f"Latitude resolution: {lat_res} degrees")
print(f"Longitude resolution: {lon_res} degrees")
# -------------------------------
# Plot fire_count
# -------------------------------
plt.figure(figsize=(8, 6))
im = plt.pcolormesh(lon, lat, fire_count, cmap='hot', shading='auto')
plt.colorbar(im, label='Number of Fires')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title(f"VIIRS Fire Count - Nepal\n{str(ds['time'].values)[:10]}")
plt.show()

# -------------------------------
# Optional: Plot FRP sum
# -------------------------------
plt.figure(figsize=(8, 6))
im = plt.pcolormesh(lon, lat, frp_sum, cmap='inferno', shading='auto')
plt.colorbar(im, label='Total FRP (MW)')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title(f"VIIRS FRP Sum - Nepal\n{str(ds['time'].values)[:10]}")
plt.show()



###############



newpath= r'S:\viirs\VIIRS_daily_gridded_0.009_nc\VIIRS_FIRE_NEPAL_20210401.nc'
newpath1 =r'C:\Users\ACER\Downloads\s5p-l3grd-no2-tropospheric-001-day-20210401-20240325.nc'
newpath2 =r'C:\Users\ACER\Downloads\s5p-l3grd-no2-tropospheric-001-day-20210401-20240325.nc'
new=xr.open_dataset(newpath)
tropomi=xr.open_dataset(newpath2)
tropomi2=xr.open_dataset(newpath2)

lat_res = float(new.lat[1] - new.lat[0])
lon_res = float(new.lon[1] - new.lon[0])

print("Latitude resolution (deg):", lat_res)
print("Longitude resolution (deg):", lon_res)

lat_res_tropo = float(tropomi.latitude[3] - tropomi.latitude[2])
lon_res_tropo = float(tropomi.longitude[3] - tropomi.longitude[2])

print("Latitude resolution (deg):", lat_res_tropo)
print("Longitude resolution (deg):", lon_res_tropo)

import numpy as np
import matplotlib.pyplot as plt

lon2d, lat2d = np.meshgrid(tropomi.longitude.values, tropomi.latitude.values)

plt.figure(figsize=(6, 6))
plt.scatter(lon2d, lat2d, s=0.2)
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("Correct Lon–Lat Grid")
plt.show()
