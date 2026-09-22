import xarray as xr
import glob
import numpy as np

# Path to your daily NetCDF files
path = r"S:\viirs\VIIRS_daily_gridded1_nc"
files = sorted(glob.glob(f"{path}\\VIIRS_FIRE_NEPAL_202104*.nc"))

# Open all daily files as a single xarray dataset
datasets = [xr.open_dataset(f) for f in files]

# Concatenate along a new 'time' dimension
ds = xr.concat(datasets, dim="time")

# Sum or aggregate variables along the time axis
monthly_ds = xr.Dataset({
    "fire_count": ds["fire_count"].sum(dim="time"),
    "frp_sum": ds["frp_sum"].sum(dim="time"),
    "frp_max": ds["frp_max"].max(dim="time"),
}, coords={"lat": ds["lat"], "lon": ds["lon"]})

# Copy attributes
monthly_ds.attrs = datasets[0].attrs
monthly_ds.attrs["aggregation"] = "Monthly: fire_count and frp_sum summed, frp_max maxed"

# Save to NetCDF
monthly_ds.to_netcdf(f"{path}\\VIIRS_FIRE_NEPAL_202104_monthly.nc")
