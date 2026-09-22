import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

files = [
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0606.002.2024073082629.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0748.002.2024073082630.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.2012.002.2024073082631.nc"
]

for file_path in files:
    ds = xr.open_dataset(file_path)

    # ------------------------------
    # Extract fire pixels (NO FILTER)
    # ------------------------------
    fire = ds[['FP_latitude', 'FP_longitude', 'FP_power', 'FP_line', 'FP_sample']]
    df_all = fire.to_dataframe().dropna().reset_index(drop=True)

    # ------------------------------
    # QA and fire mask
    # ------------------------------
    qa_array = ds['algorithm QA'].values
    fire_mask_array = ds['fire mask'].values

    df_all['qa_value'] = qa_array[
        df_all['FP_line'].values,
        df_all['FP_sample'].values
    ]
    df_all['fire_mask_value'] = fire_mask_array[
        df_all['FP_line'].values,
        df_all['FP_sample'].values
    ]

    # ------------------------------
    # Apply filters
    # ------------------------------
    qa_values = df_all['qa_value'].to_numpy()
    nominal_bits = qa_values & 0b1111111
    over_water_bit = (qa_values >> 19) & 1

    df_filt = df_all[
        (nominal_bits == 0) &
        (over_water_bit == 0) &
        (df_all['fire_mask_value'].isin([8, 9]))
    ]

    # ------------------------------
    # Observation time
    # ------------------------------
    obs_date = ds.attrs['RangeBeginningDate']
    obs_time = ds.attrs['RangeBeginningTime'][:8]
    obs_dt = datetime.strptime(obs_date + " " + obs_time, "%Y-%m-%d %H:%M:%S")

    # ------------------------------
    # Fixed color scale (shared)
    # ------------------------------
    vmin = df_all['FP_power'].min()
    vmax = df_all['FP_power'].max()

    # ------------------------------
    # Create figure
    # ------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharex=True, sharey=True)

    # ---- Unfiltered ----
    sc0 = axes[0].scatter(
        df_all['FP_longitude'],
        df_all['FP_latitude'],
        c=df_all['FP_power'],
        cmap='hot',
        s=10,
        alpha=0.7,
        vmin=vmin,
        vmax=vmax
    )
    axes[0].set_title(f'Unfiltered\n({len(df_all)} pixels)')
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')

    # ---- Filtered ----
    sc1 = axes[1].scatter(
        df_filt['FP_longitude'],
        df_filt['FP_latitude'],
        c=df_filt['FP_power'],
        cmap='hot',
        s=10,
        alpha=0.8,
        vmin=vmin,
        vmax=vmax
    )
    axes[1].set_title(f'QA + Fire Mask Filtered\n({len(df_filt)} pixels)')
    axes[1].set_xlabel('Longitude')

    # ------------------------------
    # Colorbar in its own axis
    # ------------------------------
    fig.subplots_adjust(right=0.88)  # make space
    cax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(sc1, cax=cax)
    cbar.set_label('FP Power (MW)')

    # ------------------------------
    # Main title
    # ------------------------------
    fig.suptitle(
        f'VIIRS Fire Pixels\n{os.path.basename(file_path)}\n{obs_dt}',
        fontsize=12
    )

    plt.show()
