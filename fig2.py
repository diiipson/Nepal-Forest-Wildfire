import glob
import geopandas as gpd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rioxarray  # needed for .rio accessor on fire variables too
from scipy import stats

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
# Build Nepal mask for NO2 grid
# ----------------------------
ref_clipped = no2_mean.rio.set_spatial_dims(x_dim='lon', y_dim='lat').rio.write_crs("EPSG:4326")
nepal_mask_no2 = ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False)
mask_no2 = ~np.isnan(nepal_mask_no2.values)

# ----------------------------
# Build Nepal mask for FIRE grid
# (handles case where fire grid differs from NO2 grid)
# ----------------------------
fire_ref = datasets[0]['fire_count']

# Check if fire grid matches NO2 grid
fire_lat = fire_ref['lat'].values
fire_lon = fire_ref['lon'].values
no2_lat  = no2_mean['lat'].values
no2_lon  = no2_mean['lon'].values

same_grid = (
    fire_lat.shape == no2_lat.shape and
    fire_lon.shape == no2_lon.shape and
    np.allclose(fire_lat, no2_lat, atol=1e-5) and
    np.allclose(fire_lon, no2_lon, atol=1e-5)
)

if same_grid:
    print("Fire and NO2 grids match — reusing NO2 mask for fire.")
    mask_fire = mask_no2
else:
    print("Fire and NO2 grids differ — building separate fire mask.")
    fire_ref_clipped = fire_ref.rio.set_spatial_dims(
        x_dim='lon', y_dim='lat'
    ).rio.write_crs("EPSG:4326")
    nepal_mask_fire = fire_ref_clipped.rio.clip(
        nepal.geometry, all_touched=True, drop=False
    )
    mask_fire = ~np.isnan(nepal_mask_fire.values)

# ----------------------------
# Helper: apply Nepal fire mask to a DataArray
# ----------------------------
def apply_fire_mask(da, mask):
    """Set pixels outside Nepal to NaN before any aggregation."""
    data = da.values.copy().astype(float)
    data[~mask] = np.nan
    return xr.DataArray(data, coords=da.coords, dims=da.dims)

# ----------------------------
# Sum fire variables over 7 days — NEPAL ONLY
# ----------------------------
fire_count_7d  = sum(apply_fire_mask(ds['fire_count'],  mask_fire) for ds in datasets)
frp_sum_7d     = sum(apply_fire_mask(ds['frp_sum'],     mask_fire) for ds in datasets)
day_count_7d   = sum(apply_fire_mask(ds['day_count'],   mask_fire) for ds in datasets)
night_count_7d = sum(apply_fire_mask(ds['night_count'], mask_fire) for ds in datasets)

frp_max_7d = xr.concat(
    [apply_fire_mask(ds['frp_max'], mask_fire) for ds in datasets],
    dim='time'
).max(dim='time')

print("Fire variables aggregated over Nepal only ✓")

# ----------------------------
# Mask NO2 for plotting
# ----------------------------
no2_masked = no2_mean.values.copy().astype(float)
no2_masked[~mask_no2] = np.nan

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
fire_cmap.set_bad(color='none')      # transparent where no fire / outside Nepal

no2_cmap = plt.cm.get_cmap('viridis').copy()
no2_cmap.set_bad(color='white')      # white outside Nepal

fig, axes = plt.subplots(n_rows, n_cols, figsize=(10, n_rows * 3))
fig.patch.set_facecolor('white')

axes_flat = axes.flatten()

for i, var in enumerate(fire_vars):
    ax = axes_flat[i]

    # NO2 background
    im_no2 = ax.pcolormesh(lon, lat, no2_masked, shading='auto', cmap=no2_cmap)

    # Fire overlay — mask zeros and NaNs so background shows through
    fire_data = fire_vars[var].values.copy().astype(float)
    # Outside-Nepal pixels already NaN from apply_fire_mask; mask zeros too
    fire_data[fire_data == 0] = np.nan
    fire_masked = np.ma.masked_invalid(fire_data)

    if np.ma.count(fire_masked) > 0:
        vmin = float(fire_masked.compressed().min())
        vmax = float(fire_masked.compressed().max())

        # PowerNorm (gamma=0.4): stretches low-value differences apart so
        # e.g. 1 vs 3 vs 13 fires all show clearly distinct colors.
        # gamma < 1 = more color contrast at the low end of the range.
        norm = mcolors.PowerNorm(gamma=0.4, vmin=vmin, vmax=vmax)
        im_fire = ax.pcolormesh(
            fire_ref['lon'], fire_ref['lat'],   # use fire grid coords
            fire_masked, shading='auto',
            cmap=fire_cmap, norm=norm, alpha=0.95
        )
        cbar_fire = fig.colorbar(im_fire, ax=ax, orientation='vertical',
                                 fraction=0.025, pad=0.1)
        cbar_fire.set_label(fire_titles[var], fontsize=cbar_label_size,
                            rotation=90, labelpad=8, va='bottom')
        cbar_fire.ax.tick_params(labelsize=cbar_tick_size)

        # 5 ticks equally spaced in physical length (norm space 0→1)
        # then mapped back to real data values for labels
        norm_positions = np.linspace(0, 1, 5)           # equal physical spacing
        data_values = norm.inverse(norm_positions)       # real values at those positions
        cbar_fire.set_ticks(data_values)
        if vmax <= 10:
            cbar_fire.set_ticklabels([f"{v:.1f}" for v in data_values])
        else:
            cbar_fire.set_ticklabels([f"{int(round(v))}" for v in data_values])

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
    dpi=1000,
    bbox_inches='tight'
)
plt.show()
print("Saved: fire_on_no2_background.png")

# ----------------------------
# Load CO files for April 1-7 2021
# (separate files: S:\viirs\2021_tropomi_COT, dims: latitude/longitude)
# ----------------------------
co_dir = r"S:\viirs\2021_tropomi_COT"
co_dates = [f"2021040{d}" for d in range(1, 8)]  # 20210401 … 20210407
co_files = sorted([
    f for f in glob.glob(f"{co_dir}\\*.nc")
    if any(d in f for d in co_dates)
])
print("CO files used:")
for f in co_files:
    print(f)

co_datasets = [xr.open_dataset(f) for f in co_files]

co_stack = xr.concat(
    [ds['CO_column_number_density'].squeeze() for ds in co_datasets],
    dim='time'
)
co_mean = co_stack.mean(dim='time')

# Build Nepal mask for CO grid (dims are latitude/longitude)
co_ref_clipped = co_mean.rio.set_spatial_dims(
    x_dim='longitude', y_dim='latitude'
).rio.write_crs("EPSG:4326")
nepal_mask_co = co_ref_clipped.rio.clip(nepal.geometry, all_touched=True, drop=False)
mask_co = ~np.isnan(nepal_mask_co.values)

co_masked = co_mean.values.copy().astype(float)
co_masked[~mask_co] = np.nan

# ----------------------------
# Plot: CO background + fire overlay (2-column subplot)
# ----------------------------
co_cmap = plt.cm.get_cmap('plasma').copy()
co_cmap.set_bad(color='white')

fire_cmap_co = plt.cm.get_cmap('Blues').copy()
fire_cmap_co.set_bad(color='none')

fig, axes = plt.subplots(n_rows, n_cols, figsize=(10, n_rows * 3))
fig.patch.set_facecolor('white')

axes_flat = axes.flatten()

for i, var in enumerate(fire_vars):
    ax = axes_flat[i]

    # CO background
    im_co = ax.pcolormesh(co_mean['longitude'], co_mean['latitude'], co_masked,
                          shading='auto', cmap=co_cmap)

    # Fire overlay
    fire_data = fire_vars[var].values.copy().astype(float)
    fire_data[fire_data == 0] = np.nan
    fire_masked = np.ma.masked_invalid(fire_data)

    if np.ma.count(fire_masked) > 0:
        vmin = float(fire_masked.compressed().min())
        vmax = float(fire_masked.compressed().max())
        norm = mcolors.PowerNorm(gamma=0.4, vmin=vmin, vmax=vmax)
        im_fire = ax.pcolormesh(
            fire_ref['lon'], fire_ref['lat'],
            fire_masked, shading='auto',
            cmap=fire_cmap_co, norm=norm, alpha=0.95
        )
        cbar_fire = fig.colorbar(im_fire, ax=ax, orientation='vertical',
                                 fraction=0.025, pad=0.1)
        cbar_fire.set_label(fire_titles[var], fontsize=cbar_label_size,
                            rotation=90, labelpad=8, va='bottom')
        cbar_fire.ax.tick_params(labelsize=cbar_tick_size)

        norm_positions = np.linspace(0, 1, 5)
        data_values = norm.inverse(norm_positions)
        cbar_fire.set_ticks(data_values)
        if vmax <= 10:
            cbar_fire.set_ticklabels([f"{v:.1f}" for v in data_values])
        else:
            cbar_fire.set_ticklabels([f"{int(round(v))}" for v in data_values])

    # CO colorbar
    cbar_co = fig.colorbar(im_co, ax=ax, orientation='vertical',
                           fraction=0.025, pad=0.04)
    cbar_co.set_label('CO (mol m⁻²)', fontsize=cbar_label_size,
                      rotation=90, labelpad=8, va='bottom')
    cbar_co.ax.tick_params(labelsize=cbar_tick_size)

    nepal.boundary.plot(ax=ax, edgecolor='black', linewidth=0.6)

    ax.set_xlabel('Longitude', fontsize=axis_label_size)
    ax.set_ylabel('Latitude',  fontsize=axis_label_size)
    ax.tick_params(axis='both', which='major', labelsize=tick_label_size)

if n_vars % 2 != 0:
    axes_flat[-1].set_visible(False)

plt.tight_layout()
plt.savefig(
    r"S:\viirs\pictures\sample\fire_on_co_background.png",
    dpi=1000,
    bbox_inches='tight'
)
plt.show()
print("Saved: fire_on_co_background.png")

# ----------------------------
# Normal distribution of daily fire count — by year
# ----------------------------
year_dirs = {
    2021: r"S:\viirs\merged_2021",
}

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor('white')

colors = plt.cm.tab10.colors

for idx, (year, directory) in enumerate(sorted(year_dirs.items())):
    all_files = sorted(glob.glob(f"{directory}\\{year}*_VIIRS_TROPOMI.nc"))
    if not all_files:
        print(f"No files found for {year}, skipping.")
        continue

    daily_totals = []
    for f in all_files:
        ds = xr.open_dataset(f)
        fire = apply_fire_mask(ds['fire_count'], mask_fire)
        daily_totals.append(float(np.nansum(fire.values)))
        ds.close()

    daily_totals = np.array(daily_totals)
    mu, sigma = stats.norm.fit(daily_totals)

    color = colors[idx % len(colors)]
    ax.hist(daily_totals, bins=30, density=True, alpha=0.45, color=color)
    x = np.linspace(daily_totals.min(), daily_totals.max(), 300)
    ax.plot(x, stats.norm.pdf(x, mu, sigma), color=color, linewidth=2,
            label=f"{year}  μ={mu:.1f}, σ={sigma:.1f}")
    print(f"{year}: μ={mu:.2f}, σ={sigma:.2f}, n={len(daily_totals)} days")

ax.set_xlabel('Daily Total Fire Count (Nepal)', fontsize=10)
ax.set_ylabel('Density', fontsize=10)
ax.set_title('Normal Distribution of Daily Fire Count', fontsize=11)
ax.legend(fontsize=9)
ax.tick_params(labelsize=9)

plt.tight_layout()
plt.savefig(
    r"S:\viirs\pictures\sample\fire_count_normal_dist.png",
    dpi=300,
    bbox_inches='tight'
)
plt.show()
print("Saved: fire_count_normal_dist.png")