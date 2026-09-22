import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import geopandas as gpd

# ----------------------------
# Step 1: VIIRS fire granules
# ----------------------------
files = [
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0606.002.2024073082629.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0748.002.2024073082630.nc",
    r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.2012.002.2024073082631.nc"
]

all_fires = []

################  PROCESSING SINGLE GRANULE FIRST ##############################################

import xarray as xr
import pandas as pd

# Load dataset
file_path = r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc"
ds = xr.open_dataset(file_path)

# List all variables
print(list(ds.data_vars))

# Select primary variables (without fire mask to avoid huge memory load)
primary_data = ds[['FP_line','FP_sample','FP_longitude','FP_latitude','FP_power','FP_confidence']]

# Convert to DataFrame
primary_df = primary_data.to_dataframe().dropna()

# Extract fire mask as a NumPy array
fire_mask = ds['fire mask'].values  # shape: (phony_dim_1, phony_dim_2)

# Add fire mask values to the DataFrame by indexing
primary_df['fire_mask_value'] = fire_mask[
    primary_df['FP_line'].values.astype(int),   # ensure integers
    primary_df['FP_sample'].values.astype(int)
]

# Filter for fire mask values 8 or 9
masked_df = primary_df[primary_df['fire_mask_value'].isin([8, 9])]

# Optional: drop fire_mask_value column if not needed
#masked_df = masked_df.drop(columns='fire_mask_value')

print(masked_df)


#### QA FILTER ###
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# 1. Open dataset
# ----------------------------
file_path = r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc"
ds = xr.open_dataset(file_path)

qa = ds["algorithm QA"]       # uint32 (y, x)
fire_mask = ds["fire mask"]   # uint8  (y, x)

# --------------------------------------------------
# 2. Helper function
# --------------------------------------------------
def bit(arr, n):
    return ((arr >> n) & 1).astype(bool)

# --------------------------------------------------
# 3. Identify fire pixels (fire mask)
# --------------------------------------------------
fire_pixels = fire_mask >= 7   # low, nominal, high confidence

# --------------------------------------------------
# 4. QA filtering
# --------------------------------------------------
# Nominal input data
nominal_inputs = (qa & 0b1111111) == 0

# Fire detected by algorithm
fire_detected = bit(qa, 7) | bit(qa, 10)

# Remove major artifacts
no_artifacts = (
    (~bit(qa, 16)) &   # saturation
    (~bit(qa, 17))     # glint
)

# --------------------------------------------------
# 5. Final high-quality mask
# --------------------------------------------------
high_quality_fire = (
    fire_pixels & 
    nominal_inputs & 
    fire_detected & 
    no_artifacts
)

# 6. Plot high-quality fire pixels
# --------------------------------------------------
plt.figure(figsize=(10, 8))

# Plot high-quality fire pixels as a binary heatmap (white = high quality, black = not)
plt.imshow(high_quality_fire, cmap="gray", vmin=0, vmax=1)
plt.colorbar(label="High-Quality Fire Pixels (1 = Fire Detected)")
plt.title("High-Quality Fire Pixels")
plt.axis("off")  # Hide axes for clarity
plt.tight_layout()
plt.show()

print("High-quality fire pixels:", high_quality_fire.sum().item())

# --------------------------------------------------
# 6. Apply high-quality fire mask to fire mask
# --------------------------------------------------
fire_mask_hq = fire_mask.where(high_quality_fire)

# --------------------------------------------------
# 7. Plot 1: Original fire mask and high-quality fire detections
# --------------------------------------------------
plt.figure(figsize=(14, 12))

# Plot background (original fire mask)
plt.subplot(1, 2, 1)
plt.imshow(fire_mask, cmap="gray", vmin=0, vmax=8)
plt.colorbar(label="Fire mask class")
plt.title("Original Fire Mask")
plt.axis("off")

# Overlay high-quality fires (filtered)
plt.subplot(1, 2, 2)
plt.imshow(fire_mask_hq, cmap="hot", vmin=6, vmax=8)
plt.colorbar(label="High-Quality Fire Detections")
plt.title("High-Quality Fire Detections (Filtered)")
plt.axis("off")

plt.tight_layout()
plt.show()

# --------------------------------------------------
# 8. Plot 2: QA values (overlay with fire mask)
# --------------------------------------------------
plt.figure(figsize=(12, 8))

# Plot original fire mask (gray scale)
plt.imshow(fire_mask, cmap="gray", vmin=0, vmax=8)

# Overlay QA values with transparency
plt.imshow(
    qa,
    cmap="coolwarm",
    alpha=0.5,   # Transparency level for better visualization
    vmin=0,
    vmax=32      # Full 32-bit range for QA values
)

plt.colorbar(label="QA Values (0-32)")
plt.title("Overlay: Fire Mask with QA Values")
plt.axis("off")
plt.tight_layout()
plt.show()


import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# 1. Open dataset
# ----------------------------
file_path = r"S:\viirs\VNP14IMG_002-20251219_081958\VNP14IMG.A2021091.0742.002.2024073082632.nc"
ds = xr.open_dataset(file_path)

fire_mask = ds["fire mask"]   # uint8  (y, x)

# --------------------------------------------------
# 2. Filter for fire mask pixels with value 7 or 8
# --------------------------------------------------
fire_mask_high_confidence = (fire_mask == 8) | (fire_mask == 9)

# --------------------------------------------------
# 3. Plot fire mask pixels where fire mask is 7 or 8
# --------------------------------------------------
plt.figure(figsize=(10, 8))

# Plot the fire mask values where it's 7 or 8
plt.imshow(fire_mask, cmap="hot", vmin=0, vmax=8)

# Highlight the pixels where fire_mask is 7 or 8
plt.imshow(fire_mask_high_confidence, cmap="coolwarm", alpha=0.7, vmin=0, vmax=1)

# Add colorbars for each layer
plt.colorbar(label="Fire Mask Values (0 to 8)")
plt.title("Fire Mask Pixels where fire_mask == 7 or 8")

# Turn off axes for clarity
plt.axis("off")

# Adjust layout for better presentation
plt.tight_layout()

# Show the plot
plt.show()
