import xarray as xr
import glob
import os
import pandas as pd
import numpy as np

# -----------------------
# 1. SETTINGS
# -----------------------
base_dir = r"S:\viirs"
years = [2021, 2022, 2023, 2024]
months_of_interest = [3, 4, 5, 6, 7]  # March–July
gas_folder_suffix = "_tropomi_COT"
gas_variable = "CO_column_number_density"

# -----------------------
# 2. YEAR-SPECIFIC CLUSTERS
# -----------------------
clusters_by_year = {
    2021: {
        1: {"lat_min": 27.938232421875, "lat_max": 28.839111328125, "lon_min": 81.243896484375, "lon_max": 82.342529296875},
        2: {"lat_min": 28.795166015625, "lat_max": 29.278564453125, "lon_min": 80.233154296875, "lon_max": 80.914306640625},
        3: {"lat_min": 27.169189453125, "lat_max": 27.586669921875, "lon_min": 84.298095703125, "lon_max": 85.067138671875},
    },
    2022: {
        1: {"lat_min": 27.674560546875, "lat_max": 29.168701171875, "lon_min": 80.233154296875, "lon_max": 83.089599609375},
        2: {"lat_min": 29.168701171875, "lat_max": 29.520263671875, "lon_min": 80.233154296875, "lon_max": 80.870361328125},
        3: {"lat_min": 27.059326171875, "lat_max": 27.432861328125, "lon_min": 84.715576171875, "lon_max": 85.155029296875},
    },
    2023: {
        1: {"lat_min": 27.630615234375, "lat_max": 28.026123046875, "lon_min": 82.144775390625, "lon_max": 83.529052734375},
        2: {"lat_min": 27.916259765625, "lat_max": 28.707275390625, "lon_min": 81.331787109375, "lon_max": 82.474365234375},
        3: {"lat_min": 27.103271484375, "lat_max": 27.784423828125, "lon_min": 84.254150390625, "lon_max": 85.155029296875},
    },
    2024: {
        1: {"lat_min": 27.674560546875, "lat_max": 28.773193359375, "lon_min": 81.265869140625, "lon_max": 82.760009765625},
        2: {"lat_min": 27.191162109375, "lat_max": 27.564697265625, "lon_min": 84.232177734375, "lon_max": 85.089111328125},
        3: {"lat_min": 28.817138671875, "lat_max": 29.322509765625, "lon_min": 80.233154296875, "lon_max": 80.782470703125},
    }
}

# -----------------------
# 3. FUNCTION: extract daily CO
# -----------------------
def extract_daily_co(filepath, bbox):
    ds = xr.open_dataset(filepath)
    try:
        date = pd.to_datetime(ds["datetime_start"].values[0])
        co = ds[gas_variable].sel(
            latitude=slice(bbox["lat_min"], bbox["lat_max"]),
            longitude=slice(bbox["lon_min"], bbox["lon_max"])
        )
        value = co.mean(dim=["latitude", "longitude"], skipna=True).item()
    finally:
        ds.close()
    return date, value

# -----------------------
# 4. LOOP OVER YEARS & CLUSTERS
# -----------------------
daily_results = []

for year in years:
    print(f"Processing {year}...")
    co_dir = os.path.join(base_dir, f"{year}{gas_folder_suffix}")
    co_files = sorted(glob.glob(os.path.join(co_dir, "*.nc")))

    if not co_files:
        print(f"⚠ No files found in {co_dir}")
        continue

    for cluster_id, bbox in clusters_by_year[year].items():
        daily_data = []

        for f in co_files:
            try:
                date, val = extract_daily_co(f, bbox)
            except Exception:
                continue

            if date.month in months_of_interest and not np.isnan(val):
                daily_data.append({"date": date, "year": year, "cluster": cluster_id, "CO": val})

        if daily_data:
            df = pd.DataFrame(daily_data).sort_values("date")
            df["CO_pct_change"] = df["CO"].pct_change() * 100  # percent
            daily_results.append(df)

# -----------------------
# 5. CONCAT RESULTS & SAVE
# -----------------------
daily_df = pd.concat(daily_results, ignore_index=True)
output_daily_csv = os.path.join(base_dir, "CO_daily_percent_change_top3_clusters_2021_2024.csv")
daily_df.to_csv(output_daily_csv, index=False)
print(f"✔ Daily percent change saved to: {output_daily_csv}")

# -----------------------
# 6. MONTHLY AVERAGE & MONTH-TO-MONTH CHANGE
# -----------------------
daily_df['month'] = daily_df['date'].dt.month
monthly_mean = (
    daily_df[daily_df['month'].isin(months_of_interest)]
    .groupby(['year','cluster','month'])['CO']
    .mean()
    .reset_index()
    .sort_values(['year','cluster','month'])
)
monthly_mean['month_to_month_pct_change'] = monthly_mean.groupby(['year','cluster'])['CO'].pct_change() * 100
monthly_mean['month_name'] = monthly_mean['month'].apply(lambda x: pd.to_datetime(f'2022-{x}-01').strftime('%b'))

output_monthly_csv = os.path.join(base_dir, "CO_month_to_month_change_top3_clusters_2021_2024.csv")
monthly_mean.to_csv(output_monthly_csv, index=False)
print(f"✔ Month-to-month percent change saved to: {output_monthly_csv}")

# -----------------------
# 7. PEAK ANALYSIS
# -----------------------
peak_stats = []
daily_df_nonan = daily_df.dropna(subset=['CO_pct_change'])

for (year, cluster, month), group in daily_df_nonan.groupby(['year','cluster','month']):
    group = group.sort_values('date')
    daily_max = group['CO'].max()
    daily_min = group['CO'].min()
    peak_change_within_month = ((daily_max - daily_min) / daily_min) * 100
    max_daily_spike = group['CO_pct_change'].abs().max()
    min_daily_spike = group['CO_pct_change'].min()
    
    peak_stats.append({
        'year': year,
        'cluster': cluster,
        'month': month,
        'daily_max_CO': daily_max,
        'daily_min_CO': daily_min,
        'peak_change_within_month_pct': peak_change_within_month,
        'max_daily_spike_pct': max_daily_spike,
        'min_daily_spike_pct': min_daily_spike
    })

peak_df = pd.DataFrame(peak_stats)
peak_df['month_name'] = peak_df['month'].apply(lambda x: pd.to_datetime(f'2022-{x}-01').strftime('%b'))
peak_df = peak_df.sort_values(['year','cluster','month'])

output_peak_csv = os.path.join(base_dir, "NO2_peak_episode_stats_top3_clusters_2021_2024.csv")
peak_df.to_csv(output_peak_csv, index=False)
print(f"✔ Peak episode stats saved to: {output_peak_csv}")

# -----------------------
# 8. PAPER-READY TABLE
# -----------------------
# Focus on pre-monsoon March–May
df_mam = daily_df[daily_df['month'].isin([3,4,5])].copy()

monthly_stats = []
for (year, cluster, month), group in df_mam.groupby(['year','cluster','month']):
    group = group.sort_values('date')
    daily_max = group['CO'].max()
    daily_min = group['CO'].min()
    peak_change_pct = ((daily_max - daily_min)/daily_min)*100
    daily_diff = group['CO'].diff() / group['CO'].shift(1) * 100
    max_daily_spike = daily_diff.max()
    min_daily_spike = daily_diff.min()
    monthly_stats.append({
        'year': year,
        'cluster': cluster,
        'month': month,
        'daily_max_CO': daily_max,
        'daily_min_CO': daily_min,
        'peak_change_within_month_pct': peak_change_pct,
        'max_daily_spike_pct': max_daily_spike,
        'min_daily_spike_pct': min_daily_spike
    })

monthly_df = pd.DataFrame(monthly_stats)
monthly_df['month_name'] = monthly_df['month'].apply(lambda x: pd.to_datetime(f'2022-{x}-01').strftime('%b'))

# Average peak change per year-month
avg_peak_change = monthly_df.groupby(['year','month']).agg(avg_peak_change_pct=('peak_change_within_month_pct','mean')).reset_index()
avg_peak_change['month_name'] = avg_peak_change['month'].apply(lambda x: pd.to_datetime(f'2022-{x}-01').strftime('%b'))

# Highest spike cluster per year
highest_peak = monthly_df.groupby('year').apply(lambda x: x.loc[x['peak_change_within_month_pct'].idxmax()]).reset_index(drop=True)

# Highest absolute CO per year
highest_conc = daily_df.groupby('year').apply(lambda x: x.loc[x['CO'].idxmax()]).reset_index(drop=True)
highest_conc_info = highest_conc[['year','cluster','CO']].rename(columns={'cluster':'max_CO_cluster','CO':'max_CO_mmol_m2'})

# Merge for paper table
paper_table = avg_peak_change.merge(
    highest_peak[['year','cluster','month_name','peak_change_within_month_pct']],
    on='year',
    suffixes=('_avg','_max')
).merge(highest_conc_info, on='year')

paper_table.rename(columns={
    'cluster': 'max_spike_cluster',
    'month_name_avg': 'month_avg',
    'month_name_max': 'max_spike_month',
    'peak_change_within_month_pct': 'max_spike_pct'
}, inplace=True)

paper_table = paper_table[['year','month_avg','avg_peak_change_pct',
                           'max_spike_cluster','max_spike_month','max_spike_pct',
                           'max_CO_cluster','max_CO_mmol_m2']]

output_paper_csv = os.path.join(base_dir, "NO2_monthly_avg_peak_and_maxCO_top3_clusters_2021_2024.csv")
paper_table.to_csv(output_paper_csv, index=False)
print(f"✔ Paper-ready table saved to: {output_paper_csv}")

print("\nAverage monthly peak CO change, highest spike cluster, and maximum CO concentration per year:")
print(paper_table)


# -----------------------
# 9. MAX SPIKE PER MONTH (Mar–May)
# -----------------------

# Identify the maximum peak spike per year-month across clusters
max_spike_per_month = (
    monthly_df
    .groupby(['year', 'month'])
    .apply(lambda x: x.loc[x['peak_change_within_month_pct'].idxmax()])
    .reset_index(drop=True)
)

# Keep only relevant columns
max_spike_per_month = max_spike_per_month[[
    'year',
    'month',
    'month_name',
    'cluster',
    'peak_change_within_month_pct'
]]

# Rename for clarity
max_spike_per_month.rename(columns={
    'cluster': 'max_spike_cluster',
    'peak_change_within_month_pct': 'max_spike_pct'
}, inplace=True)

# Save to CSV
output_monthly_spike_csv = os.path.join(
    base_dir,
    "NO2_max_spike_per_month_Mar_Apr_May_2021_2024.csv"
)
max_spike_per_month.to_csv(output_monthly_spike_csv, index=False)

print(f"✔ Max spike per month saved to: {output_monthly_spike_csv}")
print("\nMaximum peak spike per month (March–May):")
print(max_spike_per_month)


####march + April
# -----------------------
# Max spike combining March + April
# -----------------------

# Filter only March and April
mar_apr_df = max_spike_per_month[max_spike_per_month['month'].isin([3, 4])]

# Find the overall max spike in Mar+Apr
combined_max = mar_apr_df.loc[mar_apr_df['max_spike_pct'].idxmax()]

print("✔ Maximum spike for March + April combined:")
print(combined_max)

# Optional: format nicely
print(f"\nYear: {combined_max['year']}")
print(f"Month: {combined_max['month_name']}")
print(f"Cluster: {combined_max['max_spike_cluster']}")
print(f"Max spike %: {combined_max['max_spike_pct']:.2f}%")

###each cluster
# -----------------------
# 10. MAX SPIKE PER CLUSTER FOR MARCH–MAY
# -----------------------

# Focus on pre-monsoon months
mam_df = monthly_df[monthly_df['month'].isin([3, 4, 5])].copy()

# Compute maximum spike within each cluster for each month
max_spike_per_cluster = (
    mam_df
    .groupby(['year', 'month', 'cluster'])
    .apply(lambda x: x.loc[x['peak_change_within_month_pct'].idxmax()])
    .reset_index(drop=True)
)

# Keep relevant columns
max_spike_per_cluster = max_spike_per_cluster[[
    'year', 'month', 'month_name', 'cluster', 'peak_change_within_month_pct'
]]

# Rename for clarity
max_spike_per_cluster.rename(columns={
    'cluster': 'cluster_id',
    'peak_change_within_month_pct': 'max_spike_pct'
}, inplace=True)

# Sort for easier viewing
max_spike_per_cluster = max_spike_per_cluster.sort_values(['year', 'cluster_id', 'month'])

# Save to CSV
output_cluster_spike_csv = os.path.join(
    base_dir,
    "NO2_max_spike_per_cluster_Mar_Apr_May_2021_2024.csv"
)
max_spike_per_cluster.to_csv(output_cluster_spike_csv, index=False)

print(f"✔ Max spike per cluster for March–May saved to: {output_cluster_spike_csv}")
print("\nMaximum spike per cluster for each month (March–May) in each year:")
print(max_spike_per_cluster)


#### verify
# -----------------------
# Min, Max, and % change for Cluster 3, March 2021
# -----------------------

# Filter daily data for 2021, March, Cluster 3
cluster3_mar2021 = daily_df[
    (daily_df['year'] == 2021) &
    (daily_df['month'] == 3) &
    (daily_df['cluster'] == 3)
].copy()

if not cluster3_mar2021.empty:
    min_val = cluster3_mar2021['CO'].min()
    max_val = cluster3_mar2021['CO'].max()
    pct_change = ((max_val - min_val) / min_val) * 100

    print(f"Cluster 3, March 2021:")
    print(f"Minimum CO: {min_val:.4f}")
    print(f"Maximum CO: {max_val:.4f}")
    print(f"Percentage change: {pct_change:.2f}%")
else:
    print("No data available for Cluster 3, March 2021")




##march + April
# -----------------------
# Max percentage increase for 2024, Cluster 2 over March + April
# -----------------------

# Filter daily data
df_2024_c2_mar_apr = daily_df[
    (daily_df['year'] == 2022) &
    (daily_df['cluster'] == 3) &
    (daily_df['month'].isin([3, 4]))
].copy()

if not df_2024_c2_mar_apr.empty:
    min_val = df_2024_c2_mar_apr['CO'].min()
    max_val = df_2024_c2_mar_apr['CO'].max()
    pct_change = ((max_val - min_val) / min_val) * 100

    print("✔ 2024, Cluster 2, March + April combined:")
    print(f"Minimum CO: {min_val:.4f}")
    print(f"Maximum CO: {max_val:.4f}")
    print(f"Maximum percentage increase: {pct_change:.2f}%")
else:
    print("No data available for 2024, Cluster 2, March + April")
