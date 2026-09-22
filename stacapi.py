# import os
# import requests
# from tqdm import tqdm
# from urllib.parse import urlparse
# import xarray as xr

# # -----------------------------
# # Settings
# # -----------------------------
# # COLLECTION_2021_URL = "https://data-portal.s5p-pal.com/api/s5p-l3/no2-tropospheric/day/2024"
# COLLECTION_2021_URL = "https://data-portal.s5p-pal.com/api/s5p-l3/co/day/2024"
# DOWNLOAD_DIR = r"S:\viirs\2024_tropomi_COT"
# HEADERS = {"Accept": "application/json"}

# # Nepal bounding box [min_lon, min_lat, max_lon, max_lat]
# NEPAL_BBOX = [80.0, 26.3, 88.5, 30.5]



# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # -----------------------------
# # Function to check bbox intersection
# # -----------------------------
# def intersects(bbox1, bbox2):
#     return not (bbox1[2] < bbox2[0] or
#                 bbox1[0] > bbox2[2] or
#                 bbox1[3] < bbox2[1] or
#                 bbox1[1] > bbox2[3])

# # -----------------------------
# # Download file function
# # -----------------------------
# def download_file(url, filename=None):
#     if filename is None:
#         filename = os.path.basename(urlparse(url).path)
#     filepath = os.path.join(DOWNLOAD_DIR, filename)

#     if os.path.exists(filepath):
#         return filepath

#     with requests.get(url, stream=True) as r:
#         r.raise_for_status()
#         total = int(r.headers.get("Content-Length", 0))

#         with open(filepath, "wb") as f, tqdm(
#             total=total, unit="B", unit_scale=True, desc=filename
#         ) as bar:
#             for chunk in r.iter_content(8192):
#                 f.write(chunk)
#                 bar.update(len(chunk))
#     return filepath

# # -----------------------------
# # Load collection JSON
# # -----------------------------
# print("📦 Loading 2021 NO2 collection...")
# collection = requests.get(COLLECTION_2021_URL, headers=HEADERS).json()
# item_links = [link["href"] for link in collection["links"] if link["rel"] == "item"]
# print(f"📦 Found {len(item_links)} daily items in 2021")

# # -----------------------------
# # Download, crop, and save Nepal-only
# # -----------------------------
# for item_url in item_links:
#     item = requests.get(item_url, headers=HEADERS).json()
#     item_bbox = item.get("bbox", [-180, -90, 180, 90])

#     if intersects(item_bbox, NEPAL_BBOX):
#         assets = item.get("assets", {})
#         if "product" in assets:
#             url = assets["product"]["href"]
#             orig_filename = assets["product"].get("file:local_path", None)

#             # 1️⃣ Download global NetCDF
#             global_file = download_file(url, orig_filename)

#             # 2️⃣ Open and crop to Nepal
#             ds = xr.open_dataset(global_file)
#             ds_nepal = ds.sel(
#                 latitude=slice(NEPAL_BBOX[1], NEPAL_BBOX[3]),  # lat descending
#                 longitude=slice(NEPAL_BBOX[0], NEPAL_BBOX[2])
#             )

#             # 3️⃣ Save cropped file
#             cropped_filename = f"nepal_{orig_filename}"
#             cropped_path = os.path.join(DOWNLOAD_DIR, cropped_filename)
#             ds_nepal.to_netcdf(cropped_path)
#             print(f"✅ Saved cropped file: {cropped_path}")
#             # Close the datasets to release file handles
#             ds.close()
#             ds_nepal.close()
#             # 4️⃣ Remove original global file
#             os.remove(global_file)



# ################ FALL BACK #####################

import os
import time
import requests
from tqdm import tqdm
from urllib.parse import urlparse
import xarray as xr

# =====================================================
# SETTINGS
# =====================================================
COLLECTION_2021_URL = "https://data-portal.s5p-pal.com/api/s5p-l3/co/day/2024"
DOWNLOAD_DIR = r"S:\viirs\2024_tropomi_COT"
HEADERS = {"Accept": "application/json"}

# Nepal bounding box [min_lon, min_lat, max_lon, max_lat]
NEPAL_BBOX = [80.0, 26.3, 88.5, 30.5]

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================================
# BBOX INTERSECTION CHECK
# =====================================================
def intersects(bbox1, bbox2):
    return not (
        bbox1[2] < bbox2[0] or
        bbox1[0] > bbox2[2] or
        bbox1[3] < bbox2[1] or
        bbox1[1] > bbox2[3]
    )

# =====================================================
# DOWNLOAD FUNCTION (RESUMABLE)
# =====================================================
def download_file(url, filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    if os.path.exists(filepath):
        return filepath

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))

        with open(filepath, "wb") as f, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            desc=filename
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

    return filepath

# =====================================================
# LOAD COLLECTION
# =====================================================
print("📦 Loading 2021 NO₂ collection...")
collection = requests.get(COLLECTION_2021_URL, headers=HEADERS).json()

item_links = [
    link["href"]
    for link in collection["links"]
    if link["rel"] == "item"
]

print(f"📦 Found {len(item_links)} daily items")

# =====================================================
# MAIN LOOP: DOWNLOAD → CROP → DELETE
# =====================================================
for item_url in item_links:
    try:
        item = requests.get(item_url, headers=HEADERS, timeout=60).json()
        item_bbox = item.get("bbox", [-180, -90, 180, 90])

        # Skip if not intersecting Nepal
        if not intersects(item_bbox, NEPAL_BBOX):
            continue

        assets = item.get("assets", {})
        if "product" not in assets:
            continue

        url = assets["product"]["href"]
        orig_filename = assets["product"]["file:local_path"]

        cropped_filename = f"nepal_{orig_filename}"
        cropped_path = os.path.join(DOWNLOAD_DIR, cropped_filename)

        # ⏩ Skip already processed files
        if os.path.exists(cropped_path):
            print(f"⏩ Skipping existing: {cropped_filename}")
            continue

        # 1️⃣ Download global NetCDF
        global_file = download_file(url, orig_filename)

        # 2️⃣ Crop to Nepal
        with xr.open_dataset(global_file) as ds:
            ds_nepal = ds.sel(
                latitude=slice(NEPAL_BBOX[1], NEPAL_BBOX[3]),
                longitude=slice(NEPAL_BBOX[0], NEPAL_BBOX[2])
            )
            ds_nepal.to_netcdf(cropped_path)

        print(f"✅ Saved cropped file: {cropped_path}")

        # 3️⃣ Remove global file
        os.remove(global_file)

        # Small delay to avoid server throttling
        time.sleep(2)

    except Exception as e:
        print(f"❌ Failed on item: {item_url}")
        print(f"   Reason: {e}")
        continue

print("🎉 ALL POSSIBLE FILES PROCESSED")
