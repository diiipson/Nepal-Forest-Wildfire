import glob
import geopandas as gpd
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------
# Directory with daily files
# ----------------------------
data_dir = r"S:\viirs\2021_VIIRS_daily_gridded_0.021_nc"

# Get first 7 daily files
files = sorted(glob.glob(f"{data_dir}\\VIIRS_FIRE_NEPAL_202104*.nc"))[:7]

print("Files used:")
for f in files:
    print(f)

# ----------------------------
# Load Nepal boundary
# ----------------------------
nepal = gpd.read_file(r"C:\Users\ACER\Downloads\boundary.shp").to_crs("EPSG:4326")

# ----------------------------
# Open datasets
# ----------------------------
datasets = [xr.open_dataset(f) for f in files]

lat = datasets[0]['lat']
lon = datasets[0]['lon']

# ----------------------------
# Aggregate fire variables
# ----------------------------
fire_count_7d = sum(ds['fire_count'] for ds in datasets)
frp_sum_7d = sum(ds['frp_sum'] for ds in datasets)
day_count_7d = sum(ds['day_count'] for ds in datasets)
night_count_7d = sum(ds['night_count'] for ds in datasets)

frp_max_7d = xr.concat(
    [ds['frp_max'] for ds in datasets],
    dim='time'
).max(dim='time')

# ----------------------------
# Apply Nepal mask
# ----------------------------
ref = fire_count_7d
ref_clipped = ref.rio.set_spatial_dims(x_dim='lon', y_dim='lat').rio.write_crs("EPSG:4326")
nepal_mask = ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False)
mask = ~np.isnan(nepal_mask.values)

def apply_mask(da):
    vals = da.values.copy().astype(float)
    vals[~mask] = np.nan
    return xr.DataArray(vals, dims=da.dims, coords=da.coords)

# ----------------------------
# Store aggregated + masked variables
# ----------------------------
data_vars = {
    'fire_count': apply_mask(fire_count_7d),
    'frp_sum':    apply_mask(frp_sum_7d),
    'frp_max':    apply_mask(frp_max_7d),
    'day_count':  apply_mask(day_count_7d),
    'night_count':apply_mask(night_count_7d),
}

titles = {
    'fire_count': 'Fire Count (7 days)',
    'frp_sum': 'FRP Sum (MW, 7 days)',
    'frp_max': 'FRP Max (MW, 7 days)',
    'day_count': 'Day Count (7 days)',
    'night_count': 'Night Count (7 days)'
}

# ----------------------------
# Font sizes
# ----------------------------
axis_label_size = 7
tick_label_size = 7
cbar_label_size = 7
cbar_tick_size = 7

# ----------------------------
# Colormaps to test
# ----------------------------
colormaps = [
    ('turbo',    'Turbo'),
    ('inferno',  'Inferno'),
    ('plasma',   'Plasma'),
    ('hot',      'Hot'),
    ('YlOrRd',   'Yellow-Orange-Red'),
    ('magma',    'Magma'),
]

n_vars = len(data_vars)
n_cols = 2
n_rows = (n_vars + 1) // 2

for cmap_name, cmap_label in colormaps:

    cmap = plt.cm.get_cmap(cmap_name).copy()
    cmap.set_bad(color='white')

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(8, n_rows * 3))
    fig.patch.set_facecolor('white')
    fig.suptitle(f'Colormap: {cmap_label}', fontsize=10, fontweight='bold', y=1.01)
    axes_flat = axes.flatten()

    for i, var in enumerate(data_vars):
        ax = axes_flat[i]
        data = data_vars[var].values
        masked_data = np.ma.masked_where(np.isnan(data) | (data == 0), data)

        if np.ma.count(masked_data) == 0:
            ax.set_visible(False)
            continue

        im = ax.pcolormesh(lon, lat, masked_data, shading='auto', cmap=cmap)
        nepal.boundary.plot(ax=ax, edgecolor='black', linewidth=0.6)

        ax.set_xlabel('Longitude', fontsize=axis_label_size)
        ax.set_ylabel('Latitude', fontsize=axis_label_size)
        ax.tick_params(axis='both', which='major', labelsize=tick_label_size)

        cbar = fig.colorbar(im, ax=ax, orientation='vertical', fraction=0.045, pad=0.04)
        cbar.set_label(
            titles[var],
            fontsize=cbar_label_size,
            rotation=90,
            labelpad=8,
            va='bottom'
        )
        cbar.ax.tick_params(labelsize=cbar_tick_size)

    if n_vars % 2 != 0:
        axes_flat[-1].set_visible(False)

    plt.tight_layout()
    plt.savefig(
        f"S:\\viirs\\pictures\\sample\\all_vars_7days_{cmap_name}.png",
        dpi=150,
        bbox_inches='tight'
    )
    plt.show()
    print(f"Saved: {cmap_name}")

##########################################################
# SEPARATE CODE: Fire variables on TROPOMI NO2 background
##########################################################
import glob
import geopandas as gpd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# ----------------------------
# Nepal boundary
# ----------------------------
nepal = gpd.read_file(r"C:\Users\ACER\Downloads\boundary.shp").to_crs("EPSG:4326")

# ----------------------------
# Load 7 merged VIIRS+TROPOMI files (April 1-7 2021)
# ----------------------------
merged_dir = r"S:\viirs\merged_2021"
merged_files = sorted(glob.glob(f"{merged_dir}\\202104*_VIIRS_TROPOMI.nc"))[:7]

print("Merged files used:")
for f in merged_files:
    print(f)

datasets = [xr.open_dataset(f) for f in merged_files]

lat = datasets[0]['lat']
lon = datasets[0]['lon']

# ----------------------------
# Average NO2 over 7 days
# ----------------------------
no2_stack = xr.concat(
    [ds['tropospheric_NO2_column_number_density'].squeeze() for ds in datasets],
    dim='time'
)
no2_mean = no2_stack.mean(dim='time')

# ----------------------------
# Sum fire variables over 7 days
# ----------------------------
fire_count_7d = sum(ds['fire_count'] for ds in datasets)
frp_sum_7d    = sum(ds['frp_sum']    for ds in datasets)
day_count_7d  = sum(ds['day_count']  for ds in datasets)
night_count_7d= sum(ds['night_count']for ds in datasets)

frp_max_7d = xr.concat(
    [ds['frp_max'] for ds in datasets], dim='time'
).max(dim='time')

# ----------------------------
# Nepal mask (from NO2 grid)
# ----------------------------
ref_clipped = no2_mean.rio.set_spatial_dims(x_dim='lon', y_dim='lat').rio.write_crs("EPSG:4326")
nepal_mask  = ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False)
mask        = ~np.isnan(nepal_mask.values)

no2_masked  = no2_mean.values.copy().astype(float)
no2_masked[~mask] = np.nan

# ----------------------------
# Fire variables to overlay
# ----------------------------
fire_vars = {
    'fire_count':  fire_count_7d,
    'frp_sum':     frp_sum_7d,
    'frp_max':     frp_max_7d,
    'day_count':   day_count_7d,
    'night_count': night_count_7d,
}

fire_titles = {
    'fire_count':  'Fire Count (7 days)',
    'frp_sum':     'FRP Sum (MW, 7 days)',
    'frp_max':     'FRP Max (MW, 7 days)',
    'day_count':   'Day Count (7 days)',
    'night_count': 'Night Count (7 days)',
}

# ----------------------------
# Font sizes
# ----------------------------
axis_label_size = 7
tick_label_size = 7
cbar_label_size = 7
cbar_tick_size  = 7

# ----------------------------
# Plot: NO2 background + fire overlay (2-column subplot)
# ----------------------------
n_vars = len(fire_vars)
n_cols = 2
n_rows = (n_vars + 1) // 2

fire_cmap = plt.cm.get_cmap('Reds').copy()
fire_cmap.set_bad(color='none')          # transparent where no fire

no2_cmap  = plt.cm.get_cmap('viridis').copy()
no2_cmap.set_bad(color='white')          # white outside Nepal

fig, axes = plt.subplots(n_rows, n_cols, figsize=(10, n_rows * 3))
fig.patch.set_facecolor('white')

axes_flat = axes.flatten()

for i, var in enumerate(fire_vars):
    ax = axes_flat[i]

    # NO2 background
    im_no2 = ax.pcolormesh(lon, lat, no2_masked, shading='auto', cmap=no2_cmap)

    # Fire overlay — mask zeros so background shows through
    fire_data = fire_vars[var].values.copy().astype(float)
    fire_data[~mask] = np.nan
    fire_masked = np.ma.masked_where(np.isnan(fire_data) | (fire_data == 0), fire_data)

    if np.ma.count(fire_masked) > 0:
        vmin = fire_masked.compressed().min()
        vmax = fire_masked.compressed().max()
        norm = mcolors.LogNorm(vmin=max(vmin, 1), vmax=vmax)
        im_fire = ax.pcolormesh(lon, lat, fire_masked, shading='auto',
                                cmap=fire_cmap, norm=norm, alpha=0.95)
        cbar_fire = fig.colorbar(im_fire, ax=ax, orientation='vertical',
                                 fraction=0.025, pad=0.02)
        cbar_fire.set_label(fire_titles[var], fontsize=cbar_label_size,
                            rotation=90, labelpad=8, va='bottom')
        cbar_fire.ax.tick_params(labelsize=cbar_tick_size)

    # NO2 colorbar
    cbar_no2 = fig.colorbar(im_no2, ax=ax, orientation='vertical',
                            fraction=0.025, pad=0.04)
    cbar_no2.set_label('NO₂ (µmol/m²)', fontsize=cbar_label_size,
                       rotation=90, labelpad=8, va='bottom')
    cbar_no2.ax.tick_params(labelsize=cbar_tick_size)

    nepal.boundary.plot(ax=ax, edgecolor='black', linewidth=0.6)

    ax.set_xlabel('Longitude', fontsize=axis_label_size)
    ax.set_ylabel('Latitude',  fontsize=axis_label_size)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_size)

if n_vars % 2 != 0:
    axes_flat[-1].set_visible(False)

plt.tight_layout()
plt.savefig(
    r"S:\viirs\pictures\sample\fire_on_no2_background.png",
    dpi=300,
    bbox_inches='tight'
)
plt.show()
print("Saved: fire_on_no2_background.png")

##########
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------
# File path
# ----------------------------
file_path = r"S:\viirs\new_fitgrid_2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210401.nc"
ds = xr.open_dataset(file_path)

lat = ds['lat']
lon = ds['lon']

variables = ['fire_count', 'frp_sum', 'frp_max', 'day_count', 'night_count']
titles = ['Fire Count', 'FRP Sum (MW)', 'FRP Max (MW)', 'Day Count', 'Night Count']

# ----------------------------
# Font size settings
# ----------------------------
axis_label_size = 7     # Longitude / Latitude
tick_label_size = 7     # Axis numbers
cbar_label_size = 7     # Colorbar title
cbar_tick_size = 7     # Colorbar numbers

# ----------------------------
# Plot one-by-one
# ----------------------------
for var, title in zip(variables, titles):

    data = ds[var].values

    # Mask NaNs and zero (no fire)
    masked_data = np.ma.masked_where(np.isnan(data) | (data == 0), data)

    # Skip empty plots
    if np.ma.count(masked_data) == 0:
        print(f"No fire data for {title}, skipping...")
        continue

    plt.figure(figsize=(4, 3))

    cmap = plt.cm.turbo
    cmap.set_bad(color='black')

    im = plt.pcolormesh(
        lon,
        lat,
        masked_data,
        shading='auto',
        cmap=cmap
    )

    # Axis labels
    plt.xlabel('Longitude', fontsize=axis_label_size)
    plt.ylabel('Latitude', fontsize=axis_label_size)

    # Axis tick numbers
    plt.tick_params(axis='both', which='major', labelsize=tick_label_size)

    # Colorbar with label next to it
    cbar = plt.colorbar(im, orientation='vertical', fraction=0.045, pad=0.04)
    cbar.set_label(
        title,
        fontsize=cbar_label_size,
        rotation=90,
        labelpad=10,
        va='bottom'
    )
    cbar.ax.tick_params(labelsize=cbar_tick_size)

    # Save figure
    output_path = f"S:\\viirs\\pictures\\sample\\{var}_bright.png"
    plt.savefig(output_path, dpi=1000, bbox_inches='tight')
    plt.show()


##############################

import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

# Load dataset
file_path = r"S:\viirs\merged_2021\20210401_VIIRS_TROPOMI.nc"
ds = xr.open_dataset(file_path)

lat = ds['lat']
lon = ds['lon']

# Select the variables
no2 = ds['tropospheric_NO2_column_number_density'][0, :, :]  # remove time dimension
frp = ds['frp_count']  # could also use 'fire_count' or 'frp_max'

# Mask FRP values where 0 or NaN
frp_masked = np.ma.masked_where(np.isnan(frp) | (frp == 0), frp)

# Plot
fig, ax = plt.subplots(figsize=(12, 8))

# Plot NO2 background
no2_plot = ax.pcolormesh(lon, lat, no2, shading='auto', cmap='viridis')
cbar_no2 = fig.colorbar(no2_plot, ax=ax, orientation='vertical', fraction=0.045, pad=0.04)
cbar_no2.set_label('Tropospheric NO2 (µmol/m²)')

# Overlay FRP on top
frp_plot = ax.pcolormesh(lon, lat, frp_masked, shading='auto', cmap='hot', alpha=0.6)
cbar_frp = fig.colorbar(frp_plot, ax=ax, orientation='vertical', fraction=0.045, pad=0.08)
cbar_frp.set_label('FRP Sum (MW)')

ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('FRP Sum over Tropospheric NO2 - Nepal 2021-04-01', fontsize=14)

plt.show()


##############
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

file_path = r"S:\viirs\gridalligned_2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210401.nc"
ds = xr.open_dataset(file_path)

###############
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import pandas as pd

# -------------------------------
# Paths
# -------------------------------
data_dir = r"S:\viirs\merged_2021"
files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

# -------------------------------
# Containers
# -------------------------------
no2_list = []
fire_list = []
lat = lon = None

# -------------------------------
# Loop over daily files
# -------------------------------
for f in files:
    ds = xr.open_dataset(f)

    # Read date
    date = pd.to_datetime(ds['time'].values[0])

    # Select March–May
    if date.month in [3, 4, 5]:

        no2 = ds['tropospheric_NO2_column_number_density'][0, :, :]
        fire = ds['fire_count']  # or 'frp_sum'

        no2_list.append(no2)
        fire_list.append(fire)

        if lat is None:
            lat = ds['lat']
            lon = ds['lon']

    ds.close()

# -------------------------------
# Aggregate
# -------------------------------
no2_mam_mean = xr.concat(no2_list, dim='time').mean(dim='time')
fire_mam_sum = xr.concat(fire_list, dim='time').sum(dim='time')

# Mask zero fire values
fire_mam_masked = np.ma.masked_where(
    (fire_mam_sum == 0) | np.isnan(fire_mam_sum),
    fire_mam_sum
)

print("✔ MAM aggregation completed")

fig, ax = plt.subplots(figsize=(6,5))

# --- NO2 background (mean) ---
no2_plot = ax.pcolormesh(
    lon, lat, no2_mam_mean,
    shading='auto',
    cmap='viridis'
)

# Create divider for multiple colorbars
divider = make_axes_locatable(ax)

# Colorbar for NO2
cax1 = divider.append_axes("right", size="5%", pad=0.1)
cbar_no2 = fig.colorbar(no2_plot, cax=cax1)
cbar_no2.set_label('Mean Tropospheric NO₂ (µmol/m²)')

# --- Fire overlay (sum) ---
fire_plot = ax.pcolormesh(
    lon, lat, fire_mam_masked,
    shading='auto',
    cmap='hot',
    alpha=0.25
)

# Colorbar for Fire
cax2 = divider.append_axes("right", size="5%", pad=0.6)  # extra pad to avoid overlap
cbar_fire = fig.colorbar(fire_plot, cax=cax2)
cbar_fire.set_label('Total Fire Count (Mar–May)')

# Axes labels
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

plt.tight_layout()

# Save figure
plt.savefig(
    r"S:\viirs\pictures\alligning.png",
    dpi=1000,
    bbox_inches="tight"
)

plt.show()

##
