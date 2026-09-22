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

all_fire_dfs = []

for file_path in files:
    ds = xr.open_dataset(file_path)

    fire = ds[['FP_latitude', 'FP_longitude', 'FP_power', 'FP_line', 'FP_sample']]
    df = fire.to_dataframe().dropna().reset_index(drop=True)

    qa_array = ds['algorithm QA'].values
    fire_mask_array = ds['fire mask'].values

    df['qa_value'] = qa_array[df['FP_line'].values, df['FP_sample'].values]
    df['fire_mask_value'] = fire_mask_array[df['FP_line'].values, df['FP_sample'].values]

    qa_values = df['qa_value'].to_numpy()
    nominal_bits = qa_values & 0b1111111      # bits 0–6
    over_water_bit = (qa_values >> 19) & 1    # bit 19

    df_filtered = df[
        (nominal_bits == 0) &
        (over_water_bit == 0) &
        (df['fire_mask_value'].isin([8, 9]))
    ]

    # ---- Observation time ----
    obs_date = ds.attrs['RangeBeginningDate']
    obs_time = ds.attrs['RangeBeginningTime'][:8]
    obs_dt = datetime.strptime(obs_date + " " + obs_time, "%Y-%m-%d %H:%M:%S")

    # ------------------------------
    # PLOT EACH FILE SEPARATELY
    # ------------------------------
    plt.figure(figsize=(8, 5))
    sc = plt.scatter(
        df_filtered['FP_longitude'],
        df_filtered['FP_latitude'],
        c=df_filtered['FP_power'],
        cmap='hot',
        s=12,
        alpha=0.8
    )
    plt.colorbar(sc, label='FP Power (MW)')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title(f'VIIRS Fire Pixels\n{os.path.basename(file_path)}\n{obs_dt}')
    plt.tight_layout()
    plt.show()

    all_fire_dfs.append(df_filtered)

df_all = pd.concat(all_fire_dfs, ignore_index=True)

plt.figure(figsize=(10, 6))
sc = plt.scatter(
    df_all['FP_longitude'],
    df_all['FP_latitude'],
    c=df_all['FP_power'],
    cmap='hot',
    s=10,
    alpha=0.7
)
plt.colorbar(sc, label='FP Power (MW)')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('VIIRS Fire Pixels: QA-filtered + Fire Mask 8/9 (All Files)')
plt.show()
