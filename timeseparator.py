import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import re
from collections import defaultdict
from matplotlib.patches import Rectangle

# ------------------------------------------------
# Directory containing VIIRS files
# ------------------------------------------------
data_dir = r"S:\viirs\VNP14IMG_002-20251219_081958"

# ------------------------------------------------
# Nepal bounding box (lat/lon)
# ------------------------------------------------
NEPAL_BBOX = {
    "lon_min": 80.0,
    "lon_max": 88.5,
    "lat_min": 26.3,
    "lat_max": 30.5
}

# ------------------------------------------------
# Read all .nc files
# ------------------------------------------------
files = sorted([
    os.path.join(data_dir, f)
    for f in os.listdir(data_dir)
    if f.endswith(".nc")
])

# ------------------------------------------------
# Group files by day (A2021DDD)
# ------------------------------------------------
files_by_day = defaultdict(list)

for f in files:
    match = re.search(r"A(\d{7})", os.path.basename(f))
    if match:
        day = match.group(1)
        files_by_day[day].append(f)

# ------------------------------------------------
# Loop day-wise
# ------------------------------------------------
for day, day_files in files_by_day.items():

    df_all_day = []
    df_filt_day = []
    obs_dt = None

    for file_path in day_files:
        ds = xr.open_dataset(file_path)

        # ------------------------------
        # Extract fire pixels (no filter)
        # ------------------------------
        fire = ds[['FP_latitude', 'FP_longitude', 'FP_power',
                   'FP_line', 'FP_sample']]
        df = fire.to_dataframe().dropna().reset_index(drop=True)

        # ------------------------------
        # QA and fire mask
        # ------------------------------
        qa_array = ds['algorithm QA'].values
        fire_mask_array = ds['fire mask'].values

        df['qa_value'] = qa_array[
            df['FP_line'].values,
            df['FP_sample'].values
        ]
        df['fire_mask_value'] = fire_mask_array[
            df['FP_line'].values,
            df['FP_sample'].values
        ]

        # ------------------------------
        # Apply QA + fire mask filters
        # ------------------------------
        qa_values = df['qa_value'].to_numpy()
        nominal_bits = qa_values & 0b1111111
        over_water_bit = (qa_values >> 19) & 1

        df_filt = df[
            (nominal_bits == 0) &
            (over_water_bit == 0) &
            (df['fire_mask_value'].isin([8, 9]))
        ]

        df_all_day.append(df)
        df_filt_day.append(df_filt)

        # Capture observation time
        if obs_dt is None:
            obs_date = ds.attrs['RangeBeginningDate']
            obs_time = ds.attrs['RangeBeginningTime'][:8]
            obs_dt = datetime.strptime(
                obs_date + " " + obs_time,
                "%Y-%m-%d %H:%M:%S"
            )

        ds.close()

    # ------------------------------------------------
    # Combine all granules for the day
    # ------------------------------------------------
    if not df_all_day:
        continue

    df_all_day = pd.concat(df_all_day, ignore_index=True)
    df_filt_day = pd.concat(df_filt_day, ignore_index=True)

    if df_all_day.empty:
        continue

    # ------------------------------------------------
    # Shared color scale
    # ------------------------------------------------
    vmin = df_all_day['FP_power'].min()
    vmax = df_all_day['FP_power'].max()

    # ------------------------------------------------
    # Create figure
    # ------------------------------------------------
    fig, axes = plt.subplots(
        1, 2, figsize=(15, 5),
        sharex=True, sharey=True
    )

    # ---- Unfiltered ----
    sc0 = axes[0].scatter(
        df_all_day['FP_longitude'],
        df_all_day['FP_latitude'],
        c=df_all_day['FP_power'],
        cmap='hot',
        s=8,
        alpha=0.6,
        vmin=vmin,
        vmax=vmax
    )
    axes[0].set_title(f'Unfiltered\n({len(df_all_day)} pixels)')
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')

    # ---- Filtered ----
    sc1 = axes[1].scatter(
        df_filt_day['FP_longitude'],
        df_filt_day['FP_latitude'],
        c=df_filt_day['FP_power'],
        cmap='hot',
        s=8,
        alpha=0.8,
        vmin=vmin,
        vmax=vmax
    )
    axes[1].set_title(f'QA + Fire Mask Filtered\n({len(df_filt_day)} pixels)')
    axes[1].set_xlabel('Longitude')

    # ------------------------------------------------
    # Add Nepal bounding box to both plots
    # ------------------------------------------------
    for ax in axes:
        rect = Rectangle(
            (NEPAL_BBOX["lon_min"], NEPAL_BBOX["lat_min"]),
            NEPAL_BBOX["lon_max"] - NEPAL_BBOX["lon_min"],
            NEPAL_BBOX["lat_max"] - NEPAL_BBOX["lat_min"],
            linewidth=2,
            edgecolor='cyan',
            facecolor='none'
        )
        ax.add_patch(rect)

        # Zoom around Nepal (optional but recommended)
        ax.set_xlim(75, 95)
        ax.set_ylim(24, 32)

    # ------------------------------------------------
    # Colorbar (separate axis)
    # ------------------------------------------------
    fig.subplots_adjust(right=0.88)
    cax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(sc1, cax=cax)
    cbar.set_label('FP Power (MW)')

    # ------------------------------------------------
    # Main title
    # ------------------------------------------------
    fig.suptitle(
        f'VIIRS Fire Pixels — Day {day}\n{obs_dt.date()}',
        fontsize=12
    )

    plt.show()
