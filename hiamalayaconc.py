import xarray as xr
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import glob
import os
import re
import matplotlib.pyplot as plt

# -----------------------------
# 1. INPUT FOLDERS
# -----------------------------
no2_folder_path = r"S:\viirs\2024_tropomi_NO2"
co_folder_path  = r"S:\viirs\2024_tropomi_COT"

no2_files = sorted(glob.glob(os.path.join(no2_folder_path, "*.nc")))
co_files  = sorted(glob.glob(os.path.join(co_folder_path, "*.nc")))

print(f"Found {len(no2_files)} NO2 files")
print(f"Found {len(co_files)} CO files")

# -----------------------------
# 2. LOAD PHYSIOGRAPHIC ZONES
# -----------------------------
url = "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/main/geojson_files/physiography_nepal_updated.geojson"
zones = gpd.read_file(url)

mountain_region = zones[zones['DESCRIPTIO'].isin(['High Mountain', 'Middle Mountain'])]

# -----------------------------
# 3. FUNCTION: DAILY MEAN
# -----------------------------
def compute_daily_mean(nc_files, var_name):
    daily = []

    for f in nc_files:
        try:
            date_match = re.search(r'(\d{8})', os.path.basename(f))
            if not date_match:
                continue
            date = pd.to_datetime(date_match.group(1), format="%Y%m%d")

            ds = xr.open_dataset(f, engine="netcdf4")

            lat_name = [c for c in ds.coords if 'lat' in c.lower()][0]
            lon_name = [c for c in ds.coords if 'lon' in c.lower()][0]

            df = ds[[var_name]].to_dataframe().reset_index().dropna()

            gdf = gpd.GeoDataFrame(
                df,
                geometry=[Point(xy) for xy in zip(df[lon_name], df[lat_name])],
                crs="EPSG:4326"
            ).to_crs(mountain_region.crs)

            joined = gpd.sjoin(gdf, mountain_region, predicate="within")

            daily.append({
                "date": date,
                var_name: joined[var_name].mean()
            })

        except Exception as e:
            print(f"Skipped {os.path.basename(f)} -> {e}")

    return pd.DataFrame(daily)

# -----------------------------
# 4. COMPUTE DAILY MEANS
# -----------------------------
daily_no2 = compute_daily_mean(no2_files, "tropospheric_NO2_column_number_density")
daily_co  = compute_daily_mean(co_files,  "CO_column_number_density")

daily_df = (
    pd.merge(daily_no2, daily_co, on="date", how="outer")
    .sort_values("date")
)

# -----------------------------
# 5. INTERPOLATE MISSING DAYS
# -----------------------------
daily_df['date'] = pd.to_datetime(daily_df['date'])
daily_df = daily_df.set_index('date')

full_range = pd.date_range(
    start=daily_df.index.min(),
    end=daily_df.index.max(),
    freq='D'
)

daily_df = daily_df.reindex(full_range)

daily_df['tropospheric_NO2_column_number_density'] = (
    daily_df['tropospheric_NO2_column_number_density']
    .interpolate()
)

daily_df['CO_column_number_density'] = (
    daily_df['CO_column_number_density']
    .interpolate()
)

# Convert NO2 µmol → mmol
daily_df['NO2_mmol'] = daily_df['tropospheric_NO2_column_number_density'] / 1000

daily_df = daily_df.reset_index().rename(columns={'index': 'date'})

# -----------------------------
# 6. SAVE DAILY CSV
# -----------------------------
daily_df.to_csv(
    r"S:\viirs\daily_NO2_CO_interpolated_2024.csv",
    index=False
)

# -----------------------------
# 7. SEPARATE DAILY PLOTS (1000 DPI)
# -----------------------------
plt.figure(figsize=(10,5))
plt.plot(daily_df['date'], daily_df['NO2_mmol'], color='blue')
plt.xlabel("Date")
plt.ylabel("Tropospheric NO2 Column Density (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\NO2_daily_2024.png", dpi=1000)
plt.show()

plt.figure(figsize=(10,5))
plt.plot(daily_df['date'], daily_df['CO_column_number_density'], color='orange')
plt.xlabel("Date")
plt.ylabel("Total CO Column Density (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\CO_daily_2024.png", dpi=1000)
plt.show()

# -----------------------------
# 8. MONTHLY MAXIMUM
# -----------------------------
monthly_max = (
    daily_df
    .set_index('date')
    .resample('M')
    .max()
)

monthly_max = monthly_max[['NO2_mmol', 'CO_column_number_density']]

# -----------------------------
# 9. MONTH-TO-MONTH % CHANGE
# -----------------------------
monthly_pct_change = monthly_max.pct_change() * 100

monthly_pct_change = monthly_pct_change.rename(columns={
    'NO2_mmol': 'NO2_monthly_max_%change',
    'CO_column_number_density': 'CO_monthly_max_%change'
})

# Save monthly results
monthly_pct_change.to_csv(
    r"S:\viirs\monthly_max_percentage_change_2024.csv"
)



# -----------------------------
# 10. MONTHLY % CHANGE PLOTS
# -----------------------------
plt.figure(figsize=(10,5))
plt.plot(
    monthly_pct_change.index,
    monthly_pct_change['NO2_monthly_max_%change'],
    marker='o'
)
plt.xlabel("Month")
plt.ylabel("NO₂ Monthly Max Change (%)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\NO2_monthly_percent_change_2021.png", dpi=1000)
plt.show()

plt.figure(figsize=(10,5))
plt.plot(
    monthly_pct_change.index,
    monthly_pct_change['CO_monthly_max_%change'],
    marker='s'
)
plt.xlabel("Month")
plt.ylabel("CO Monthly Max Change (%)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\CO_monthly_percent_change_2021.png", dpi=1000)
plt.show()

print("\nMonthly maximum percentage change (%)")
print(monthly_pct_change.round(2))
