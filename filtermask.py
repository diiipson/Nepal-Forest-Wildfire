import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------
# 1. Load dataset
# ------------------------------
file_path = r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc"
ds = xr.open_dataset(file_path)

# ------------------------------
# 2. Extract fire pixel variables (1D)
# ------------------------------
fire = ds[['FP_latitude', 'FP_longitude', 'FP_power', 'FP_line', 'FP_sample']]
df = fire.to_dataframe().dropna().reset_index(drop=True)

# ------------------------------
# 3. Map fire pixels to 2D fire mask
# ------------------------------
fire_mask = ds['fire mask'].values
df['fire_mask_value'] = fire_mask[df['FP_line'].values, df['FP_sample'].values]

# ------------------------------
# 4. Filter high-confidence fire pixels (mask = 8 or 9)
# ------------------------------
df_filtered = df[df['fire_mask_value'].isin([8, 9])]

# ------------------------------
# 5. Plotting
# ------------------------------
# Full fire pixels
fp_lat = df['FP_latitude'].values
fp_lon = df['FP_longitude'].values
fp_power = df['FP_power'].values

# Filtered fire pixels
fp_lat_filt = df_filtered['FP_latitude'].values
fp_lon_filt = df_filtered['FP_longitude'].values
fp_power_filt = df_filtered['FP_power'].values

# Create figure with 2 subplots
fig, axs = plt.subplots(1, 2, figsize=(16, 6), sharex=True, sharey=True)

# Plot all fire pixels
sc1 = axs[0].scatter(fp_lon, fp_lat, c=fp_power, cmap='hot', s=10, alpha=0.7)
axs[0].set_title('All Fire Pixels')
axs[0].set_xlabel('Longitude')
axs[0].set_ylabel('Latitude')
plt.colorbar(sc1, ax=axs[0], label='FP Power (MW)')

# Plot filtered fire pixels
sc2 = axs[1].scatter(fp_lon_filt, fp_lat_filt, c=fp_power_filt, cmap='hot', s=10, alpha=0.7)
axs[1].set_title('Filtered Fire Pixels (Mask 8 or 9)')
axs[1].set_xlabel('Longitude')
plt.colorbar(sc2, ax=axs[1], label='FP Power (MW)')

plt.suptitle('VIIRS Fire Pixels: All vs High-Confidence')
plt.tight_layout()
plt.show()
