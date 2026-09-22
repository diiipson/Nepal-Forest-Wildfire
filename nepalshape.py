import cartopy.io.shapereader as shpreader
import geopandas as gpd
import matplotlib.pyplot as plt

# ==================================================
# 1. Load Cartopy Natural Earth countries (Admin 0)
# ==================================================
shapefile = shpreader.natural_earth(resolution='10m', 
                                    category='cultural', 
                                    name='admin_0_countries')

# ==================================================
# 2. Read all countries into GeoDataFrame
# ==================================================
records = list(shpreader.Reader(shapefile).records())

countries = []
for rec in records:
    countries.append({
        'name': rec.attributes['NAME_LONG'],
        'geometry': rec.geometry
    })

gdf = gpd.GeoDataFrame(countries, crs='EPSG:4326', geometry='geometry')

# ==================================================
# 3. Filter for Nepal
# ==================================================
nepal = gdf[gdf['name'] == 'Nepal']

# ==================================================
# 4. Save to shapefile
# ==================================================
output_file = r"C:\Users\ACER\Downloads\Nepal_boundary_from_cartopy.shp"
nepal.to_file(output_file)
print(f"Nepal shapefile saved successfully to {output_file}!")

# ==================================================
# 5. Visualize Nepal boundary
# ==================================================
fig, ax = plt.subplots(figsize=(8,8))
nepal.boundary.plot(ax=ax, edgecolor='blue', linewidth=2)
ax.set_title("Nepal Boundary from Cartopy/Natural Earth")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()


#################
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# 1. Load shapefile
shapefile_path = r"C:\Users\ACER\Downloads\districts0___2026_May_31_09_55_56\districts0\districts0.shp"
nepal_gdf = gpd.read_file(shapefile_path)

# 2. Create persistence data
persistence_data = {
    "District": [
        "Bardiya", "Banke", "Dang", "Surkhet", "Parsa", "Bara",
        "Kailali", "Dadeldhura", "Chitwan", "Salyan", "Kanchanpur",
        "Arghakhanchi", "Baitadi", "Rupandehi", "Palpa", "Kapilbastu", "Makwanpur"
    ],
    "Years_Present": [4, 4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1]
}
persistence_df = pd.DataFrame(persistence_data)

# 3. Clean names
nepal_gdf['DISTRICT_clean'] = nepal_gdf['DISTRICT'].str.strip().str.upper()
persistence_df['District_clean'] = persistence_df['District'].str.strip().str.upper()

# 4. Merge
merged_gdf = nepal_gdf.merge(persistence_df[['District_clean','Years_Present']],
                             left_on='DISTRICT_clean',
                             right_on='District_clean',
                             how='left')
merged_gdf['Years_Present'] = merged_gdf['Years_Present'].fillna(0).astype(int)

# 5. Plot map with gradient
fig, ax = plt.subplots(1, 1, figsize=(12, 14))
colors_list = ['#d9d9d9', '#ffffb2', '#fecc5c', '#fd8d3c', '#e31a1c']  # 0=gray, 1-4 yellow→red
cmap = mcolors.ListedColormap(colors_list)
bounds = [0,1,2,3,4,5]
norm = mcolors.BoundaryNorm(bounds, cmap.N)

merged_gdf.plot(column='Years_Present',
                cmap=cmap,
                linewidth=0.8,
                edgecolor='black',
                norm=norm,
                legend=True,
                legend_kwds={'label': "Years in Top-3 Wildfire Clusters (2021-2024)",
                             'orientation': "vertical"},
                ax=ax)

ax.set_title("Persistence of Wildfire Hotspot Districts in Nepal (2021–2024)", fontsize=16)
ax.axis('off')

# # 6. Annotate districts **on top of polygons**
# for idx, row in merged_gdf.iterrows():
#     if row['Years_Present'] > 0:  # only annotate hotspot districts
#         centroid = row['geometry'].centroid
#         ax.text(x=centroid.x, 
#                 y=centroid.y + 0.1,  # offset slightly upward
#                 s=row['DISTRICT'],
#                 horizontalalignment='center',
#                 fontsize=4,
#                 fontweight='bold',
#                 color='black')

plt.tight_layout()
plt.show()

### new district hotspot

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --------------------------------------------------
# 1. Load Nepal districts shapefile
# --------------------------------------------------
shapefile_path = r"C:\Users\ACER\Downloads\districts0___2026_May_31_09_55_56\districts0\districts0.shp"
nepal_gdf = gpd.read_file(shapefile_path)

# --------------------------------------------------
# 2. Persistence data (years in top-3 wildfire clusters)
# --------------------------------------------------
persistence_data = {
    "District": [
        "Bardiya", "Banke", "Dang", "Surkhet", "Parsa", "Bara",
        "Kailali", "Dadeldhura", "Chitwan", "Salyan", "Kanchanpur",
        "Arghakhanchi", "Baitadi", "Rupandehi", "Palpa",
        "Kapilbastu", "Makwanpur"
    ],
    "Years_Present": [4, 4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1]
}
persistence_df = pd.DataFrame(persistence_data)

# --------------------------------------------------
# 3. Clean district names
# --------------------------------------------------
nepal_gdf['DISTRICT_clean'] = nepal_gdf['DISTRICT'].str.strip().str.upper()
persistence_df['District_clean'] = persistence_df['District'].str.strip().str.upper()

# --------------------------------------------------
# 4. Merge shapefile with persistence data
# --------------------------------------------------
merged_gdf = nepal_gdf.merge(
    persistence_df[['District_clean', 'Years_Present']],
    left_on='DISTRICT_clean',
    right_on='District_clean',
    how='left'
)

merged_gdf['Years_Present'] = merged_gdf['Years_Present'].fillna(0).astype(int)

# --------------------------------------------------
# 5. Define your original color scheme
# --------------------------------------------------
colors_list = ['#d9d9d9', '#ffffb2', '#fecc5c', '#fd8d3c', '#e31a1c']
cmap = mcolors.ListedColormap(colors_list)
bounds = [0, 1, 2, 3, 4, 5]
norm = mcolors.BoundaryNorm(bounds, cmap.N)

# --------------------------------------------------
# 6. Plot map with THIN bottom colorbar
# --------------------------------------------------
fig, ax = plt.subplots(1, 1, figsize=(14, 6))

merged_gdf.plot(
    column='Years_Present',
    cmap=cmap,
    norm=norm,
    linewidth=0.7,
    edgecolor='0.3',
    legend=True,
    legend_kwds={
        'label': "Times District Appeared in Top-3 Wildfire Hotspots (2021–2024)",
        'orientation': "horizontal",
        'shrink': 0.3,   # controls length
        'aspect': 45,    # controls thickness (higher = thinner)
        'pad': 0.04
    },
    ax=ax
)

# --------------------------------------------------
# 7. Annotate hotspot district names
# --------------------------------------------------
for _, row in merged_gdf.iterrows():
    if row['Years_Present'] > 0:
        centroid = row['geometry'].centroid
        ax.text(
            x=centroid.x,
            y=centroid.y,
            s=row['DISTRICT'].title(),
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=5.5,
            fontweight='semibold',
            color='black'
        )

# --------------------------------------------------
# 8. Final formatting
# --------------------------------------------------
ax.axis('off')
plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.08)
fig.savefig(
    r"S:\viirs\pictures\District\NEWMAP.png",  # path and filename
    dpi=1000,        # high resolution for publications
    bbox_inches='tight'    # True if you want a transparent background
)
plt.show()
