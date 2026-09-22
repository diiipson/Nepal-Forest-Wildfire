import xarray as xr

file = r"S:\viirs\AP_MAY_VIIRS_daily_gridded_0.021_nc\"
ds = xr.open_dataset(file)
print(ds.info)
print(ds["fire_count"])

import matplotlib.pyplot as plt

ds["fire_count"].plot(
    figsize=(8, 6),
    cmap="hot",
    cbar_kwargs={"label": "FRP (MW)"}
)

plt.title("VIIRS Daily FRP Sum – Nepal (2021-04-01)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()


####
import xarray as xr
import os
import glob
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------------------
# 1. Set folder and get files
# ---------------------------
folder = r"S:\viirs\AP_MAY_VIIRS_daily_gridded_0.021_nc"
nc_files = sorted(glob.glob(os.path.join(folder, "*.nc")))

dates = []
fire_counts = []

# ---------------------------
# 2. Loop through each file
# ---------------------------
for f in nc_files:
    ds = xr.open_dataset(f)
    
    # compute total fire count (scalar)
    total_fc = ds["fire_count"].sum(dim=("lat", "lon"))
    fire_counts.append(total_fc.item())
    
    # extract date from filename (example: VIIRS_FIRE_NEPAL_20210401.nc)
    date_str = os.path.basename(f).split("_")[-1].replace(".nc", "")
    dates.append(datetime.strptime(date_str, "%Y%m%d"))
    
    # Optional: save a map for each day
    plt.figure(figsize=(8, 6))
    ds["fire_count"].plot(
        cmap="hot",
        cbar_kwargs={"label": "fire count"}
    )
    plt.title(f"VIIRS Daily Fire Count – Nepal ({date_str})")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()
    
    ds.close()

# ---------------------------
# 3. Plot time series of total fire counts
# ---------------------------
plt.figure(figsize=(10, 5))
plt.plot(dates, fire_counts, marker="o", color="red")
plt.xlabel("Date")
plt.ylabel("Total Fire Count")
plt.title("Daily VIIRS Fire Count – Nepal")
plt.grid(True)
plt.tight_layout()
plt.show()


################

import xarray as xr
import os
import glob
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------------------
# 1. Set folder and get files
# ---------------------------
folder = r"S:\viirs\VIIRS_daily_gridded_0.021_nc"
nc_files = sorted(glob.glob(os.path.join(folder, "*.nc")))

dates = []
fire_counts = []

# Initialize variable to store cumulative fire count
cumulative_fire = None

# ---------------------------
# 2. Loop through each file
# ---------------------------
for f in nc_files:
    ds = xr.open_dataset(f)
    
    # Compute total fire count (scalar) for time series
    total_fc = ds["fire_count"].sum(dim=("lat", "lon"))
    fire_counts.append(total_fc.item())
    
    # Extract date from filename
    date_str = os.path.basename(f).split("_")[-1].replace(".nc", "")
    dates.append(datetime.strptime(date_str, "%Y%m%d"))
    
    # Accumulate fire counts across all days
    if cumulative_fire is None:
        cumulative_fire = ds["fire_count"].copy()  # first file
    else:
        cumulative_fire += ds["fire_count"]        # add subsequent files
    
    ds.close()

# ---------------------------
# 3. Plot time series of total fire counts
# ---------------------------
plt.figure(figsize=(10, 5))
plt.plot(dates, fire_counts, marker="o", color="red")
plt.xlabel("Date")
plt.ylabel("Total Fire Count")
plt.title("Daily VIIRS Fire Count – Nepal")
plt.grid(True)
plt.tight_layout()
plt.show()

# ---------------------------
# 4. Plot final cumulative map
# ---------------------------
plt.figure(figsize=(8, 6))
cumulative_fire.plot(
    cmap="hot",
    cbar_kwargs={"label": "Cumulative Fire Count"}
)
plt.title("Cumulative VIIRS Fire Count – Nepal (All Days)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()


