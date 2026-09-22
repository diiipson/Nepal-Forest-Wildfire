# Data Sources

This pipeline consumes several external datasets. None of the raw or derived
data files are stored in this repository (see `.gitignore`); this document
records where each input comes from so the pipeline is reproducible from
scratch. Fields marked **TODO** are gaps in provenance found in the current
scripts and should be filled in by whoever holds the original download
details.

## 1. VIIRS Active Fire product (VNP14IMG)

- **What**: Suomi-NPP VIIRS 375 m Active Fire granules (per-orbit NetCDF).
  Variables used in this pipeline: `FP_latitude`, `FP_longitude`, `FP_power`,
  `FP_line`, `FP_sample`, `fire mask`, `algorithm QA`.
- **Product**: VNP14IMG, Collection 2 (`VNP14IMG_002-...` local folder names
  reflect this).
- **Provider**: NASA LAADS DAAC / LANCE (Level-1 and Atmosphere Archive &
  Distribution System).
- **Suggested DOI**: `10.5067/VIIRS/VNP14IMG.002` — **TODO**: confirm this is
  the exact collection/version used, and record the actual download tool
  (e.g. LAADS DAAC order, `earthdata` API, or FIRMS) and date range fetched.
- **Local layout expected by scripts**: a folder of `.nc` granules named like
  `VNP14IMG.A2021091.0742.002.2024073082632.nc`, referenced via
  `VNP14IMG_002-<download-timestamp>` directories (e.g. `filtering.py`,
  `regrid.py`, `finalregridalgorithm.py`).

## 2. TROPOMI / Sentinel-5P Level-3 gridded products (NO2, CO)

- **What**: Daily gridded tropospheric NO2 column and CO column density.
- **Provider**: Copernicus Sentinel-5P, distributed via the S5P-PAL data
  portal (`https://data-portal.s5p-pal.com`), accessed through its STAC-like
  collection API.
- **Access script**: [stacapi.py](stacapi.py) — queries a collection URL
  (e.g. `.../api/s5p-l3/co/day/2024`), filters items whose bounding box
  intersects Nepal (`[80.0, 26.3, 88.5, 30.5]`), downloads the global daily
  NetCDF, crops it to Nepal, and discards the global file.
- **Local layout expected**: folders such as `2024_tropomi_NO2/` and
  `2024_tropomi_COT/` containing cropped `nepal_*.nc` files.
- **TODO**: some scripts (e.g. `combinetropomiviirs.py`, `fig2.py`) instead
  read one-off files from `C:\Users\ACER\Downloads\...` (e.g.
  `April1_s5p-no2-cropped.nc`). Confirm whether these were produced by
  `stacapi.py` or downloaded manually, and consolidate to one acquisition
  path.

## 3. Nepal administrative boundaries (district/province shapefiles)

- **Files referenced in code**:
  - `C:\Users\ACER\Downloads\Nepal Districts Shapefile Download\03_DISTRICT\DISTRICT.shp`
    (used in `PROVINCEAREA.py`)
  - `C:\Users\ACER\Downloads\boundary.shp` (used in `fig2.py`,
    `firecountstat.py`, `methodology1.py`, `methodology2.py`)
- **Provider**: **TODO** — not recorded in code. Likely candidates for Nepal
  administrative boundaries include ICIMOD, Nepal's Survey Department, or
  DIVA-GIS/OCHA HDX. Record the exact source, version/year, and license
  before relying on this for publication, since administrative boundaries
  are frequently revised.
- **CRS**: reprojected to `EPSG:4326` (WGS84) in code.

## 4. National boundary (country outline)

- **What**: World admin-0 country boundaries, used to draw/clip the Nepal
  outline in `nepalshape.py`.
- **Provider**: Natural Earth (via `cartopy.io.shapereader`, resolution
  `10m`, category `cultural`, `admin_0_countries`). Natural Earth data is
  public domain.

## 5. Derived products (produced by this pipeline, not raw inputs)

- Daily gridded VIIRS fire products (`VIIRS_FIRE_NEPAL_YYYYMMDD.nc`,
  CF-1.10-compliant, variables `fire_count`, `frp_sum`, `frp_max` on a
  ~0.022° grid over Nepal) — produced by the regridding scripts, see
  [README.md](README.md#regridding-viirs-granules-to-a-daily-nepal-grid).
- Merged VIIRS + TROPOMI daily files (`*_VIIRS_TROPOMI.nc`) — produced by
  `combinetropomiviirs.py`.
- `fire_daily_2021_2024.csv` — a tabular daily fire-count summary used by
  `boxplot_fire.py`. **TODO**: identify/commit the script that generates this
  CSV from the gridded NetCDFs (none of the current scripts appear to write
  it), so the whole chain from raw granules to this file is scripted.

## Known reproducibility gaps

- Every script currently hardcodes absolute Windows paths
  (`S:\viirs\...`, `C:\Users\ACER\Downloads\...`). Running this pipeline on
  another machine requires manually editing paths in each script — see the
  "Reproducibility caveats" section of [README.md](README.md).
- Several intermediate output directory names encode ad hoc processing
  history (e.g. `gridalligned_2024_VIIRS_daily_gridded_0.021_nc`,
  `fitgrid_2022_VIIRS_daily_gridded_0.021_nc`,
  `new_fitgrid_2021_VIIRS_daily_gridded_0.021_nc`). These are not
  self-documenting; if kept long-term, record what distinguishes each one.
