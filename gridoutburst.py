import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# --- Load dataset ---
newpath = r'S:\viirs\2021_VIIRS_daily_gridded_0.021_nc\VIIRS_FIRE_NEPAL_20210101.nc'
ds = xr.open_dataset(newpath)
fire_count = ds['fire_count'].squeeze()

# --- Mask zeros ---
masked_fire = np.ma.masked_where(fire_count.values == 0, fire_count.values)

# --- Use exact lat/lon bounds for extent ---
lat_edges = np.zeros(ds['lat_bnds'].shape[0] + 1)
lat_edges[:-1] = ds['lat_bnds'][:, 0]   # lower bounds of each cell
lat_edges[-1] = ds['lat_bnds'][-1, 1]   # upper bound of last cell

lon_edges = np.zeros(ds['lon_bnds'].shape[0] + 1)
lon_edges[:-1] = ds['lon_bnds'][:, 0]   # left bounds
lon_edges[-1] = ds['lon_bnds'][-1, 1]   # right bound of last cell

extent = [lon_edges[0], lon_edges[-1], lat_edges[0], lat_edges[-1]]

# --- Plot ---
fig, ax = plt.subplots(figsize=(12,10))
cmap = plt.cm.hot.copy()
cmap.set_bad(color='white')

im = ax.imshow(
    masked_fire,
    origin='lower',
    extent=extent,
    cmap=cmap,
    interpolation='none',
    aspect='auto'
)

# --- Overlay grid lines exactly on bounds ---
for lat in lat_edges:
    ax.axhline(lat, color='black', linewidth=0.3, linestyle=':')
for lon in lon_edges:
    ax.axvline(lon, color='black', linewidth=0.3, linestyle=':')

# --- Labels and colorbar ---
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('VIIRS Daily Fire Count - 2021-01-01 (Nepal)')

cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Fire Count')

plt.tight_layout()
plt.show()



############################ himalaya
# ==================================================
# 0. Imports
# ==================================================
# ==================================================
# 0. Imports
# ==================================================
import xarray as xr
import glob
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import rioxarray
import pandas as pd

# ==================================================
# 1. Paths
# ==================================================
data_dir = r"S:\viirs\2021_tropomi_NO2"
shp_path = r"C:\Users\ACER\Downloads\boundary.shp"

files = sorted(glob.glob(os.path.join(data_dir, "*.nc")))

# ==================================================
# 2. Nepal boundary
# ==================================================
nepal = gpd.read_file(shp_path).to_crs("EPSG:4326")

# ==================================================
# 3. Read files safely & filter MAM
# ==================================================
co_list = []

for f in files:
    try:
        ds = xr.open_dataset(f)

        # Read file date
        date = pd.to_datetime(ds["datetime_start"].values[0])

        # Filter March–April–May
        if date.month not in [4]:
            ds.close()
            continue

        # Extract CO directly (time already exists!)
        co = ds["tropospheric_NO2_column_number_density"]

        co_list.append(co)
        ds.close()

    except Exception as e:
        print(f"Skipping unreadable file: {os.path.basename(f)}")
        print(e)

print(f"Valid MAM files used: {len(co_list)}")

# ==================================================
# 4. Combine & average
# ==================================================
co_all = xr.concat(co_list, dim="time")
co_mam_mean = co_all.mean(dim="time", skipna=True)

# ==================================================
# 5. CRS & clip
# ==================================================
co_mam_mean = co_mam_mean.rio.write_crs("EPSG:4326")

co_clip = co_mam_mean.rio.clip(
    nepal.geometry,
    nepal.crs,
    drop=True
)

# ==================================================
# 6. Plot map
# ==================================================
fig, ax = plt.subplots(figsize=(8, 10))

co_clip.plot(
    ax=ax,
    cmap="inferno",
    cbar_kwargs={"label": "Mean CO column (mol m⁻²)"}
)

nepal.boundary.plot(ax=ax, edgecolor="black", linewidth=1)

ax.set_title("Mean CO Concentration over Nepal (March–May 2024)", fontsize=14)
ax.set_axis_off()

plt.tight_layout()
plt.show()

####################################  

import geopandas as gpd
url = "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/main/geojson_files/physiography_nepal_updated.geojson"
gdf = gpd.read_file(url)
gdf.plot()

import geopandas as gpd
import matplotlib.pyplot as plt

# Use raw string to avoid escape character issues
file_path = r"C:\Users\ACER\Documents\physiography_nepal_updated.geojson"

# Read the GeoJSON file
gdf = gpd.read_file(file_path)

# Plot the GeoDataFrame
gdf.plot()

# Show the plot
plt.show()


######
file_path = r"S:\viirs\gridalligned_2021_VIIRS_daily_gridded_0.021_nc"

import xarray as xr
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import glob
import os

# -----------------------------
# 1. FOLDER CONTAINING NETCDF FILES
# -----------------------------
folder_path = r"S:\viirs\gridalligned_2024_VIIRS_daily_gridded_0.021_nc"  # folder with all daily NetCDF files
nc_files = sorted(glob.glob(os.path.join(folder_path, "*.nc")))

# -----------------------------
# 2. LOAD PHYSIOGRAPHIC ZONES
# -----------------------------
url = "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/main/geojson_files/physiography_nepal_updated.geojson"
gdf = gpd.read_file(url)

# -----------------------------
# 3. FILTER FILES FOR MARCH, APRIL, MAY
# -----------------------------
# Assuming filenames include YYYYMMDD, e.g., "VIIRS_20210301.nc"
def file_in_mam(filename):
    basename = os.path.basename(filename)
    # Extract YYYYMMDD part
    yyyymmdd = ''.join(filter(str.isdigit, basename))
    month = int(yyyymmdd[4:6])
    return month in [3, 4, 5]

nc_files_mam = [f for f in nc_files if file_in_mam(f)]
print(f"Processing {len(nc_files_mam)} files for March–May")

# -----------------------------
# 4. PROCESS EACH FILE
# -----------------------------
all_fire_data = []

for f in nc_files_mam:
    ds = xr.open_dataset(f, engine='netcdf4')
    
    # Replace 'fire_count' with your variable name
    fire_var = 'fire_count'
    
    # Flatten to points
    fire_df = ds[fire_var].to_dataframe().reset_index()
    fire_df = fire_df.dropna(subset=[fire_var])
    
    # Create geometry
    geometry = [Point(xy) for xy in zip(fire_df['lon'], fire_df['lat'])]
    fire_gdf = gpd.GeoDataFrame(fire_df, geometry=geometry, crs="EPSG:4326")
    
    # Match CRS
    fire_gdf = fire_gdf.to_crs(gdf.crs)
    
    # Spatial join
    fire_with_region = gpd.sjoin(fire_gdf, gdf, how="inner", predicate='within')
    
    # Add date from filename
    basename = os.path.basename(f)
    yyyymmdd = ''.join(filter(str.isdigit, basename))
    fire_with_region['date'] = pd.to_datetime(yyyymmdd, format="%Y%m%d")
    
    all_fire_data.append(fire_with_region[['DESCRIPTIO', fire_var, 'date']])

# -----------------------------
# 5. COMBINE ALL DAYS
# -----------------------------
combined_fire = pd.concat(all_fire_data, ignore_index=True)

# -----------------------------
# 6. AGGREGATE BY REGION (TOTAL FOR MARCH–MAY)
# -----------------------------
fire_by_region = combined_fire.groupby('DESCRIPTIO')[fire_var].sum().reset_index()

# -----------------------------
# 7. CALCULATE PERCENTAGE
# -----------------------------
total_fires = fire_by_region[fire_var].sum()
fire_by_region['fire_pct'] = fire_by_region[fire_var] / total_fires * 100

# -----------------------------
# 8. DISPLAY RESULTS
# -----------------------------
print(fire_by_region.sort_values('fire_pct', ascending=False))

# Optional: save to CSV
fire_by_region.to_csv(r"S:\viirs\fire_count_percentage_by_region_MAM_2021.csv", index=False)


######TIME SERIES HIMALAYA
import xarray as xr
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import glob
import os
import re
import matplotlib.pyplot as plt

# -----------------------------
# 1. FOLDER CONTAINING DAILY NC FILES
# -----------------------------
no2_folder_path = r"S:\viirs\2021_tropomi_NO2"
co_folder_path = r"S:\viirs\2021_tropomi_COT"

no2_files = sorted(glob.glob(os.path.join(no2_folder_path, "*.nc")))
co_files = sorted(glob.glob(os.path.join(co_folder_path, "*.nc")))

print(f"Found {len(no2_files)} daily NO2 files.")
print(f"Found {len(co_files)} daily CO files.")

# -----------------------------
# 2. LOAD PHYSIOGRAPHIC ZONES
# -----------------------------
url = "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/main/geojson_files/physiography_nepal_updated.geojson"
gdf = gpd.read_file(url)

# Combine High Mountain and Middle Mountain
mountain_region = gdf[gdf['DESCRIPTIO'].isin(['High Mountain', 'Middle Mountain'])]

# -----------------------------
# 3. FUNCTION TO COMPUTE DAILY MEAN WITH ERROR HANDLING
# -----------------------------
def compute_daily_mean(nc_files, var_name):
    daily_list = []
    for f in nc_files:
        try:
            basename = os.path.basename(f)
            match = re.search(r'(\d{8})', basename)
            if not match:
                print(f"Skipping file, date not found: {basename}")
                continue
            date = pd.to_datetime(match.group(1), format="%Y%m%d")

            # Open dataset
            ds = xr.open_dataset(f, engine='netcdf4')

            # Detect coordinate names
            lat_name, lon_name = None, None
            for dim in ds.coords:
                if 'lat' in dim.lower():
                    lat_name = dim
                if 'lon' in dim.lower():
                    lon_name = dim
            if lat_name is None or lon_name is None:
                print(f"Skipping file, no lat/lon found: {basename}")
                continue

            if var_name not in ds:
                print(f"Skipping file, variable {var_name} not found: {basename}")
                continue

            # Flatten to DataFrame
            df = ds[[var_name]].to_dataframe().reset_index()
            df = df.dropna(subset=[var_name])
            if df.empty:
                print(f"No valid data in file: {basename}")
                continue

            # Create GeoDataFrame
            geometry = [Point(xy) for xy in zip(df[lon_name], df[lat_name])]
            gdf_data = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

            # Match CRS
            gdf_data = gdf_data.to_crs(mountain_region.crs)

            # Spatial join
            data_in_region = gpd.sjoin(gdf_data, mountain_region, how='inner', predicate='within')

            # Compute daily mean
            mean_val = data_in_region[var_name].mean() if not data_in_region.empty else float('nan')

            daily_list.append({'date': date, var_name: mean_val})

        except Exception as e:
            print(f"Skipping file due to error: {basename} -> {e}")
            continue

    return pd.DataFrame(daily_list)

# -----------------------------
# 4. COMPUTE DAILY MEANS
# -----------------------------
daily_no2_df = compute_daily_mean(no2_files, 'tropospheric_NO2_column_number_density')
daily_co_df = compute_daily_mean(co_files, 'CO_column_number_density')

# Merge by date
daily_df = pd.merge(daily_no2_df, daily_co_df, on='date', how='outer').sort_values('date')
print("Merged daily NO2 & CO dataframe:")
print(daily_df.head())

# -----------------------------
# 5. PLOT DAILY TIME SERIES
# -----------------------------
plt.figure(figsize=(12,6))
plt.plot(daily_df['date'], daily_df['tropospheric_NO2_column_number_density'],
         marker='o', linestyle='-', label='NO2')
plt.plot(daily_df['date'], daily_df['CO_column_number_density'],
         marker='s', linestyle='--', label='CO')
plt.title("Daily Tropospheric NO2 & CO over High + Middle Mountains (2024)")
plt.xlabel("Date")
plt.ylabel("Column Density (molecules/cm²)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# -----------------------------
# 6. SAVE CSV
# -----------------------------
output_csv = r"S:\viirs\daily_NO2_CO_High_Middle_Mountains_2024.csv"
daily_df.to_csv(output_csv, index=False)
print(f"Daily NO2 & CO time series saved to: {output_csv}")

# -----------------------------
# 5. PLOT DAILY TIME SERIES (COMMON UNIT: mmol/m²)
# -----------------------------
import matplotlib.pyplot as plt

# -----------------------------
# CONVERT UNITS TO mmol/m²
# -----------------------------
# NO2: µmol → mmol
daily_df['NO2_mmol'] = daily_df['tropospheric_NO2_column_number_density'] / 1000
# CO is already in mmol, so we can just use it directly

# -----------------------------
# PLOT NO2
# -----------------------------
plt.figure(figsize=(12,6))
plt.plot(daily_df['date'], daily_df['NO2_mmol'], linestyle='-', color='blue')
plt.title("Daily Tropospheric NO2 over High + Middle Mountains (2024)")
plt.xlabel("Date")
plt.ylabel("NO2 (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.show()

# -----------------------------
# PLOT CO
# -----------------------------
plt.figure(figsize=(12,6))
plt.plot(daily_df['date'], daily_df['CO_column_number_density'], linestyle='-', color='orange')
plt.title("Daily Tropospheric CO over High + Middle Mountains (2024)")
plt.xlabel("Date")
plt.ylabel("CO (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.show()
##interpolate

# -----------------------------
# INTERPOLATE MISSING DAYS
# -----------------------------
# Ensure 'date' is datetime
daily_df['date'] = pd.to_datetime(daily_df['date'])

# Set 'date' as index
daily_df.set_index('date', inplace=True)

# Reindex to full daily range
full_range = pd.date_range(start=daily_df.index.min(), end=daily_df.index.max(), freq='D')
daily_df = daily_df.reindex(full_range)

# Interpolate missing values linearly
daily_df['tropospheric_NO2_column_number_density'] = daily_df['tropospheric_NO2_column_number_density'].interpolate(method='linear')
daily_df['CO_column_number_density'] = daily_df['CO_column_number_density'].interpolate(method='linear')

# Also convert NO2 to mmol/m² after interpolation
daily_df['NO2_mmol'] = daily_df['tropospheric_NO2_column_number_density'] / 1000

# Reset index to have 'date' as a column again
daily_df = daily_df.reset_index().rename(columns={'index': 'date'})

# -----------------------------
# PLOT DAILY TIME SERIES (interpolated)
# -----------------------------
# -----------------------------
# INTERPOLATE MISSING DAYS
# -----------------------------
daily_df['date'] = pd.to_datetime(daily_df['date'])
daily_df.set_index('date', inplace=True)

# Full daily range
full_range = pd.date_range(start=daily_df.index.min(), end=daily_df.index.max(), freq='D')
daily_df = daily_df.reindex(full_range)

# Interpolate missing values
daily_df['tropospheric_NO2_column_number_density'] = daily_df['tropospheric_NO2_column_number_density'].interpolate(method='linear')
daily_df['CO_column_number_density'] = daily_df['CO_column_number_density'].interpolate(method='linear')

# Convert NO2 to mmol/m²
daily_df['NO2_mmol'] = daily_df['tropospheric_NO2_column_number_density'] / 1000

# Reset index to have 'date' column
daily_df = daily_df.reset_index().rename(columns={'index': 'date'})

# -----------------------------
# PLOT NO2 (separate)
# -----------------------------
plt.figure(figsize=(10,5))
plt.plot(daily_df['date'], daily_df['NO2_mmol'],  color='blue')
# plt.title("Daily Tropospheric NO2 over High + Middle Mountains (2024, interpolated)")
plt.xlabel("Date")
plt.ylabel("NO2 (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\NO2_High_Middle_Mountains_2021.png", dpi=1000)
plt.show()

# -----------------------------
# PLOT CO (separate)
# -----------------------------
plt.figure(figsize=(10,5))
plt.plot(daily_df['date'], daily_df['CO_column_number_density'], color='orange')
# plt.title("Daily Tropospheric CO over High + Middle Mountains (2024, interpolated)")
plt.xlabel("Date")
plt.ylabel("CO (mmol/m²)")
plt.grid(True)
plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\CO_High_Middle_Mountains_2021.png", dpi=1000)
plt.show()

##max change


----------------------------
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
plt.savefig(r"S:\viirs\pictures\NO2_monthly_percent_change_2024.png", dpi=1000)
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
plt.savefig(r"S:\viirs\pictures\CO_monthly_percent_change_2024.png", dpi=1000)
plt.show()

########### plot
import geopandas as gpd
import matplotlib.pyplot as plt

# URL for physiographic zones GeoJSON
url = "https://raw.githubusercontent.com/idioticode/physiographic_zones_of_nepal/main/geojson_files/physiography_nepal_updated.geojson"

# Load the physiographic zones
gdf = gpd.read_file(url)

# Plot
fig, ax = plt.subplots(figsize=(8, 10))
gdf.plot(column='DESCRIPTIO', ax=ax, legend=True, cmap='tab20')
ax.set_title("Physiographic Zones of Nepal")
ax.set_axis_off()

plt.show()


########### combine
# ================================
# Nepal Physiographic Zones Map
# ================================
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import pyproj
import numpy as np
from matplotlib.patches import Patch

# -------------------------------
# Load GeoJSON
# -------------------------------
url = (
    "https://raw.githubusercontent.com/idioticode/"
    "physiographic_zones_of_nepal/main/geojson_files/"
    "physiography_nepal_updated.geojson"
)
gdf = gpd.read_file(url)

# -------------------------------
# Correct mapping for legend
# -------------------------------
# Map dataset values to desired legend names
zone_mapping = {
    "High Mountain": "Higher Himalaya",
    "Middle Mountain": "Lesser Himalaya",
    "Hill": "Hill",
    "Siwalik": "Siwalik",
    "Tarai": "Terai"
}

gdf['Zone_Label'] = gdf['DESCRIPTIO'].map(zone_mapping)

# -------------------------------
# Assign colors for each category
# -------------------------------
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import pyproj
import numpy as np
from matplotlib.patches import Patch

# -------------------------------
# Load GeoJSON
# -------------------------------
url = (
    "https://raw.githubusercontent.com/idioticode/"
    "physiographic_zones_of_nepal/main/geojson_files/"
    "physiography_nepal_updated.geojson"
)
gdf = gpd.read_file(url)

# -------------------------------
# Correct mapping for legend
# -------------------------------
# Map dataset values to desired legend names
zone_mapping = {
    "High Mountain": "Higher Himalaya",
    "Middle Mountain": "Lesser Himalaya",
    "Hill": "Hill",
    "Siwalik": "Siwalik",
    "Tarai": "Terai"
}

gdf['Zone_Label'] = gdf['DESCRIPTIO'].map(zone_mapping)

# -------------------------------
# Assign colors for each category
# -------------------------------
colors = {
    "Higher Himalaya": "#8B4513",   # brown
    "Lesser Himalaya": "#228B22",   # dark green
    "Hill": "#7CFC00",              # light green
    "Siwalik": "#FFD700",           # gold
    "Terai": "#F0E68C"              # khaki
}

gdf['color'] = gdf['Zone_Label'].map(colors)

# -------------------------------
# Convert CRS to Web Mercator
# -------------------------------
gdf = gdf.to_crs(epsg=3857)

# -------------------------------
# Nepal bounding box
# -------------------------------
min_lon, min_lat = 80.0, 26.3
max_lon, max_lat = 88.5, 30.5
project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
minx_m, miny_m = project.transform(min_lon, min_lat)
maxx_m, maxy_m = project.transform(max_lon, max_lat)
bbox = box(minx_m, miny_m, maxx_m, maxy_m)
gdf = gdf[gdf.intersects(bbox)]

# -------------------------------
# Plot map
# -------------------------------
fig, ax = plt.subplots(figsize=(4, 3))

# Plot polygons
gdf.plot(color=gdf['color'], edgecolor='black', linewidth=0.8, alpha=0.7, ax=ax)

# Nepal outline
outline = gdf.dissolve()
outline.boundary.plot(ax=ax, color='black', linewidth=1.5)

# -------------------------------
# Custom legend
# -------------------------------
legend_elements = [
    Patch(facecolor="#8B4513", edgecolor='black', label="Higher Himalaya"),
    Patch(facecolor="#228B22", edgecolor='black', label="Lesser Himalaya"),
    Patch(facecolor="#7CFC00", edgecolor='black', label="Hill"),
    Patch(facecolor="#FFD700", edgecolor='black', label="Siwalik"),
    Patch(facecolor="#F0E68C", edgecolor='black', label="Terai")
]
ax.legend(handles=legend_elements, title="Physiographic Zones")

# -------------------------------
# Latitude/Longitude ticks
# -------------------------------
lon_ticks = np.arange(80, 89, 1)
lat_ticks = np.arange(26, 31, 1)
xticks = [project.transform(lon, min_lat)[0] for lon in lon_ticks]
yticks = [project.transform(min_lon, lat)[1] for lat in lat_ticks]
ax.set_xticks(xticks)
ax.set_yticks(yticks)
ax.set_xticklabels([f"{lon}°E" for lon in lon_ticks])
ax.set_yticklabels([f"{lat}°N" for lat in lat_ticks])

# -------------------------------
# Titles
# -------------------------------
ax.set_title("Physiographic Zones of Nepal", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\aoi\nepal_physio_zones_corrected.png", dpi=300)
plt.show()


# -------------------------------
# Convert CRS to Web Mercator
# -------------------------------
gdf = gdf.to_crs(epsg=3857)

# -------------------------------
# Nepal bounding box
# -------------------------------
min_lon, min_lat = 80.0, 26.3
max_lon, max_lat = 88.5, 30.5
project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
minx_m, miny_m = project.transform(min_lon, min_lat)
maxx_m, maxy_m = project.transform(max_lon, max_lat)
bbox = box(minx_m, miny_m, maxx_m, maxy_m)
gdf = gdf[gdf.intersects(bbox)]

# -------------------------------
# Plot map
# -------------------------------
fig, ax = plt.subplots(figsize=(7, 8))

# Plot polygons
gdf.plot(color=gdf['color'], edgecolor='black', linewidth=0.8, alpha=0.7, ax=ax)

# Nepal outline
outline = gdf.dissolve()
outline.boundary.plot(ax=ax, color='black', linewidth=1.5)

# -------------------------------
# Custom legend
# -------------------------------
legend_elements = [
    Patch(facecolor="#8B4513", edgecolor='black', label="Higher Himalaya"),
    Patch(facecolor="#228B22", edgecolor='black', label="Lesser Himalaya"),
    Patch(facecolor="#7CFC00", edgecolor='black', label="Hill"),
    Patch(facecolor="#FFD700", edgecolor='black', label="Siwalik"),
    Patch(facecolor="#F0E68C", edgecolor='black', label="Terai")
]
ax.legend(handles=legend_elements, title="Physiographic Zones")

# -------------------------------
# Latitude/Longitude ticks
# -------------------------------
lon_ticks = np.arange(80, 89, 1)
lat_ticks = np.arange(26, 31, 1)
xticks = [project.transform(lon, min_lat)[0] for lon in lon_ticks]
yticks = [project.transform(min_lon, lat)[1] for lat in lat_ticks]
ax.set_xticks(xticks)
ax.set_yticks(yticks)
ax.set_xticklabels([f"{lon}°E" for lon in lon_ticks])
ax.set_yticklabels([f"{lat}°N" for lat in lat_ticks])

# -------------------------------
# Titles
# -------------------------------
# ax.set_title("Physiographic Zones of Nepal", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

plt.tight_layout()
plt.savefig(r"S:\viirs\pictures\aoi\nepal_physio_zones_corrected.png", dpi=1000)
plt.show()
