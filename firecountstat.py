import xarray as xr
import geopandas as gpd
import numpy as np
import pandas as pd
import glob
import os

# ==================================================
# 1. Paths
# ==================================================
data_dirs = {
    2021: r"S:\viirs\gridalligned_2021_VIIRS_daily_gridded_0.021_nc",
    2022: r"S:\viirs\gridalligned_2022_VIIRS_daily_gridded_0.021_nc",
    2023: r"S:\viirs\gridalligned_2023_VIIRS_daily_gridded_0.021_nc",
    2024: r"S:\viirs\gridalligned_2024_VIIRS_daily_gridded_0.021_nc",
}

shape_file = r"C:\Users\ACER\Downloads\boundary.shp"
nepal = gpd.read_file(shape_file).to_crs("EPSG:4326")

# ==================================================
# 2. Container for statistics
# ==================================================
annual_stats = []

# ==================================================
# 3. Loop over years
# ==================================================
for year, data_dir in data_dirs.items():

    files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
    if not files:
        print(f"No files for {year}")
        continue

    daily_fire_counts = []
    nepal_mask = None

    for f in files:
        ds = xr.open_dataset(f)

        fire = ds["fire_count"].astype("float32")
        fire = fire.rio.write_crs("EPSG:4326")

        # --- Create Nepal mask once ---
        if nepal_mask is None:
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
            nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

        fire_clip = fire.where(nepal_mask == 1)

        # --- Daily fire count over Nepal ---
        daily_fire_counts.append(
            fire_clip.sum(dim=["lat", "lon"]).item()
        )

        ds.close()

    daily_fire_counts = np.array(daily_fire_counts)

    # ==================================================
    # 4. Annual statistics
    # ==================================================
    annual_stats.append({
        "Year": year,
        "Total_fire_count": np.nansum(daily_fire_counts),
        "Mean_daily_fire": np.nanmean(daily_fire_counts),
        "Median_daily_fire": np.nanmedian(daily_fire_counts),
        "Max_daily_fire": np.nanmax(daily_fire_counts),
        "Fire_active_days": np.sum(daily_fire_counts > 0)
    })

    print(f"✔ Completed statistics for {year}")

# ==================================================
# 5. Convert to DataFrame
# ==================================================
df_fire_stats = pd.DataFrame(annual_stats)
print(df_fire_stats)


# ==================================================
# Monthly fire percentage statistics
# ==================================================
monthly_stats = []

for year, data_dir in data_dirs.items():

    files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))
    if not files:
        continue

    monthly_counts = {m: 0.0 for m in range(1, 13)}
    nepal_mask = None

    for f in files:
        ds = xr.open_dataset(f)

        fire = ds["fire_count"].astype("float32")
        fire = fire.rio.write_crs("EPSG:4326")

        date = pd.to_datetime(ds["time"].values[0])
        month = date.month

        if nepal_mask is None:
            tmp = fire.rio.clip(nepal.geometry, all_touched=True, drop=False)
            nepal_mask = xr.where(tmp.notnull(), 1, np.nan)

        fire_clip = fire.where(nepal_mask == 1)

        monthly_counts[month] += fire_clip.sum(dim=["lat", "lon"]).item()
        ds.close()

    # --- Convert to percentages ---
    annual_total = sum(monthly_counts.values())

    for month, count in monthly_counts.items():
        monthly_stats.append({
            "Year": year,
            "Month": month,
            "Monthly_fire_count": count,
            "Percentage_of_annual_fire": (count / annual_total) * 100 if annual_total > 0 else np.nan
        })

# ==================================================
# Convert to DataFrame
# ==================================================
df_monthly_fire = pd.DataFrame(monthly_stats)
print(df_monthly_fire)
