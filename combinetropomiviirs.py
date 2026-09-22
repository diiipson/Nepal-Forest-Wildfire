import xarray as xr

# -------------------------
# File paths
# -------------------------
viirs_path = r'S:\viirs\new_fitgrid_2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210101.nc'
# viirs_path = r'S:\viirs\fitgrid_2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210101.nc'
# viirs_path = r'S:\viirs\VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210401.nc'
tropomi_path = r'C:\Users\ACER\Downloads\April1_s5p-no2-cropped.nc'
output_path = r'S:\viirs\VIIRS_TROPOMI_combined_20210401.nc'

# -------------------------
# Open datasets
# -------------------------
vi = xr.open_dataset(viirs_path)
tr = xr.open_dataset(tropomi_path)

###################### JUUUST SUNGLEEE ##############
import matplotlib.pyplot as plt

# Select first (and only) time slice
# no2 = tr['tropospheric_NO2_column_number_density'].isel(time=0)

# plt.figure(figsize=(8,6))
# plt.pcolormesh(tr['longitude'], tr['latitude'], no2, shading='auto', cmap='viridis')
# plt.colorbar(label='NO2 column density [mol/m²]')
# plt.xlabel('Longitude')
# plt.ylabel('Latitude')
# plt.title('TROPOMI Tropospheric NO2 (original grid)')
# plt.show()


# -------------------------
# Inspect resolutions (optional)
# -------------------------
print("VIIRS resolution (deg) lat/lon:", float(vi.lat[1]-vi.lat[0]), float(vi.lon[1]-vi.lon[0]))
print("TROPOMI resolution (deg) lat/lon:", float(tr.latitude[1]-tr.latitude[0]), float(tr.longitude[1]-tr.longitude[0]))

print("VIIRS lat (first 5):", vi.lat.values[:5])
print("VIIRS lon (first 5):", vi.lon.values[:5])
print("TROPOMI lat (first 5):", tr.latitude.values[:5])
print("TROPOMI lon (first 5):", tr.longitude.values[:5])
print("VIIRS total lat points:", len(vi.lat))
print("VIIRS total lon points:", len(vi.lon))

print("TROPOMI total lat points:", len(tr.latitude))
print("TROPOMI total lon points:", len(tr.longitude))
# -------------------------
# Select first time slice of TROPOMI NO2
# -------------------------
tr_no2 = tr['tropospheric_NO2_column_number_density'].isel(time=0)

# -------------------------
# Rename TROPOMI coords to match VIIRS
# -------------------------
tr_no2 = tr_no2.rename({'latitude': 'lat', 'longitude': 'lon'})

# -------------------------
# Interpolate TROPOMI NO2 to VIIRS grid
# -------------------------
tr_interp = tr_no2.interp(
    lat=vi.lat,
    lon=vi.lon,
    method='nearest'  # safest for discrete counts; use 'linear' for continuous smoothing
)

# -------------------------
# Combine VIIRS + TROPOMI into one Dataset
# -------------------------
combined = xr.Dataset(
    data_vars={
        'fire_count': vi['fire_count'],
        'frp_sum': vi['frp_sum'],
        'frp_max': vi['frp_max'],
        'no2': tr_interp
    },
    coords={
        'lat': vi.lat,
        'lon': vi.lon,
        'time': vi.time  # keeps VIIRS time
    },
    attrs={
        'description': 'VIIRS fire + TROPOMI NO2 on same 0.02197° grid over Nepal',
        'source': 'VIIRS VNP14IMG + TROPOMI S5P'
    }
)

# -------------------------
# Save combined dataset
# -------------------------
combined.to_netcdf(output_path)
print(f"Combined dataset saved to: {output_path}")

# -------------------------
# Quick summary
# -------------------------
import matplotlib.pyplot as plt

# Create a figure with 2 subplots side by side
fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)

# -------------------------
# Plot VIIRS fire count
# -------------------------
im1 = axes[0].pcolormesh(
    combined.lon, combined.lat, combined['fire_count'],
    shading='auto', cmap='hot'
)
axes[0].set_title('VIIRS Fire Count')
axes[0].set_xlabel('Longitude')
axes[0].set_ylabel('Latitude')
fig.colorbar(im1, ax=axes[0], label='Fire Count')

# -------------------------
# Plot TROPOMI NO2
# -------------------------
im2 = axes[1].pcolormesh(
    combined.lon, combined.lat, combined['no2'],
    shading='auto', cmap='viridis'
)
axes[1].set_title('TROPOMI NO2 (regridded)')
axes[1].set_xlabel('Longitude')
axes[1].set_ylabel('Latitude')
fig.colorbar(im2, ax=axes[1], label='NO2 column density')

plt.show()









####################GPT SUGGESTION
# Create a grid description file from VIIRS grid (lat/lon)
cdo griddes VIIRS_FIRE_NEPAL_20210401.nc > viirs_grid.txt

# Regrid TROPOMI to VIIRS grid (nearest neighbor)
cdo remapnn,viirs_grid.txt TROPOMI_s5p.nc TROPOMI_on_VIIRS.nc

# Or bilinear interpolation for continuous fields
cdo remapbil,viirs_grid.txt TROPOMI_s5p.nc TROPOMI_on_VIIRS_bilinear.nc


remapnn → nearest-neighbor (like method='nearest' in Python)

remapbil → bilinear (like method='linear' in Python)

cdo merge VIIRS_FIRE_NEPAL_20210401.nc TROPOMI_on_VIIRS.nc VIIRS_TROPOMI_combined.nc
