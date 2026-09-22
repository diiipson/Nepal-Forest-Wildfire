# VIIRS Nepal Fire & TROPOMI Air Quality Analysis Pipeline

Scripts for filtering and regridding VIIRS (VNP14IMG) active-fire detections
over Nepal, combining them with TROPOMI/Sentinel-5P NO2 and CO columns, and
producing the statistics/figures used in the associated analysis.

This README documents the pipeline as it exists today. **This pass added
version control, dependency, licensing, and data-provenance documentation
around the existing scripts — the scripts' internal logic was not changed**
(see [Reproducibility caveats](#reproducibility-caveats) below for what that
means in practice).

## Sample outputs

Example figures from the pipeline, in [`Picture samples/`](Picture%20samples):

| Cluster classification (regional) | Cluster classification (zoomed, with hotspot) |
|---|---|
| ![Cluster classification over the Nepal fire domain](Picture%20samples/Cluster1.png) | ![Zoomed cluster classification with a detected hotspot in red](Picture%20samples/Cluster2.png) |

Spatial cluster/hotspot classification of the gridded fire domain (from the
hotspot/cluster analysis scripts, e.g. [`hotspot.py`](hotspot.py) and
[`PROVINCEAREA.py`](PROVINCEAREA.py)) — colored cells are distinct clusters;
red cells in the zoomed view mark a detected hotspot.

![Tropospheric NO2 vs. VIIRS fire count across site clusters and years](Picture%20samples/Figure_8.jpg)

Tropospheric NO2 (green, left axis) against VIIRS fire count (red, right
axis) across multiple site clusters and years, showing NO2 tracking the
fire season peak around March–May (from the VIIRS + TROPOMI combination
step, see [Combining VIIRS fire grids with TROPOMI](#4-combining-viirs-fire-grids-with-tropomi)).

A combined/merged version of the cluster maps is also available as
[`cluster_combined.tif`](Picture%20samples/cluster_combined.tif) (not
shown inline — GitHub does not render TIFF images in Markdown).

## Repository layout

```
.
├── README.md            <- this file
├── DATA_SOURCES.md       <- provenance of every external dataset used
├── LICENSE               <- MIT license
├── CITATION.cff          <- machine-readable citation metadata
├── requirements.txt      <- Python dependencies
├── .gitignore            <- excludes data files, figures, local tool config
├── Picture samples/      <- curated example output figures (tracked despite .gitignore)
└── *.py                  <- analysis scripts (see below)
```

Raw and derived data (NetCDF, shapefiles, CSVs, figures) are **not** stored
in this repository — see `.gitignore` and `DATA_SOURCES.md`.

## Pipeline stages

The 27 scripts fall into these groups. Several scripts are iterative
variants explored while developing the method rather than distinct pipeline
steps — these are noted explicitly so you don't run all of them expecting
different results.

### 1. Data acquisition
- [`stacapi.py`](stacapi.py) — downloads daily TROPOMI/S5P-PAL NO2 or CO
  NetCDFs, keeps only granules intersecting the Nepal bounding box, crops
  them, and discards the global files.

### 2. Granule-level QA & fire-mask filtering (VIIRS VNP14IMG)
- [`FILECHECK.py`](FILECHECK.py) — quick structural inspection of a single
  granule (`ds.info()`).
- [`filtering.py`](filtering.py), [`filtermask.py`](filtermask.py) — map
  1D fire-pixel records (`FP_line`/`FP_sample`) onto the 2D `fire mask`
  array and filter to high-confidence classes (8/9).
- [`qafilter.py`](qafilter.py), [`qafilter1.py`](qafilter1.py) — apply the
  `algorithm QA` bitmask (nominal-input bits, over-water bit) together with
  the fire-mask filter; `qafilter1.py` is an earlier/unfiltered comparison
  variant.

### 3. Regridding VIIRS granules to a daily Nepal grid
Bins per-orbit fire pixels into a fixed ~0.022° lat/lon grid over Nepal
(`lat 26.3–30.5`, `lon 80.0–88.5`), producing daily CF-compliant NetCDFs with
`fire_count`, `frp_sum`, `frp_max`.
- [`finalregridalgorithm.py`](finalregridalgorithm.py) — marked in-code as
  **"WORKING + CF-1.10 COMPLIANT"**; treat this as the canonical version of
  the regridding algorithm.
- [`regrid.py`](regrid.py), [`regridvirsstartingpoint.py`](regridvirsstartingpoint.py),
  [`lonlatsumerror.py`](lonlatsumerror.py), [`timeseparator.py`](timeseparator.py) —
  earlier iterations/debugging passes of the same algorithm (e.g. tracking
  down a lon/lat summation bug, exploring per-day time grouping). Kept for
  history; not needed if you only want the final output.
- [`monthlygrid.py`](monthlygrid.py) — aggregates daily grids into a
  monthly sum/max composite.
- [`dailyanalysis.py`](dailyanalysis.py), [`gridoutburst.py`](gridoutburst.py) —
  quick-look plots of a single daily grid file.

### 4. Combining VIIRS fire grids with TROPOMI
- [`combinetropomiviirs.py`](combinetropomiviirs.py) — merges a daily VIIRS
  fire grid with a same-day TROPOMI NO2 file.
- [`hiamalayaconc.py`](hiamalayaconc.py) — reads paired NO2/CO TROPOMI
  folders for regional concentration analysis.

### 5. Statistics and figures
- [`firecountstat.py`](firecountstat.py) — aggregates gridded fire counts
  per district (2021–2024) using a Nepal district shapefile.
- [`no2costat.py`](no2costat.py) — CO column density statistics by
  year/month cluster.
- [`boxplot_fire.py`](boxplot_fire.py) — seasonal (Mar–May) boxplots of
  daily fire counts by year, with skewness reported for a figure caption.
  Reads a pre-aggregated `fire_daily_2021_2024.csv` (see the open item in
  `DATA_SOURCES.md` — no script here currently produces this file).
- [`fig2.py`](fig2.py) — composite figure from a week of merged
  VIIRS+TROPOMI files.
- [`methodology.py`](methodology.py), [`methodology1.py`](methodology1.py),
  [`methodology2.py`](methodology2.py) — successive iterations of a
  methodology figure combining gridded fire data, district boundaries, and
  connected-component cluster labeling (`scipy.ndimage.label`).
- [`hotspot.py`](hotspot.py) — Getis-Ord Gi* local hotspot statistic
  (`esda.G_Local` on a `libpysal` lattice weights matrix), with hotspot
  contours extracted via `skimage.measure`.
- [`PROVINCEAREA.py`](PROVINCEAREA.py) — province/district-level fire
  aggregation and burned-area estimation using connected-component
  labeling.

### 6. Reference geometry
- [`nepalshape.py`](nepalshape.py) — builds a Nepal boundary from Natural
  Earth admin-0 country polygons (via `cartopy`).

See [DATA_SOURCES.md](DATA_SOURCES.md) for what each input dataset is, where
it comes from, and known provenance gaps.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

`cartopy` and `esda`/`libpysal` can be easier to install via conda if pip
wheels are unavailable for your platform:

```bash
conda create -n viirs-nepal python=3.11
conda activate viirs-nepal
conda install -c conda-forge xarray netcdf4 h5netcdf geopandas shapely rioxarray pyproj cartopy libpysal esda scikit-image matplotlib requests tqdm
```

## Running the scripts

Each script is a standalone entry point (`python <script>.py`), run in the
order implied by the pipeline stages above. **Before running any script,
open it and update the hardcoded input/output paths** (`S:\viirs\...`,
`C:\Users\ACER\Downloads\...`) to match your local data layout — see
[Reproducibility caveats](#reproducibility-caveats).

## Reproducibility caveats

This documentation pass deliberately did **not** touch script internals, to
avoid silently changing scientific results. As a result:

- **Paths are hardcoded per-script**, often to a specific Windows drive
  (`S:\`) and a specific user's Downloads folder. To run on another machine,
  every path assignment near the top of each script must be edited by hand.
- **Some scripts contain multiple concatenated experiments** in one file
  (e.g. `filtering.py`, `qafilter.py` run several exploratory blocks back to
  back with duplicate imports) rather than a single clear entry point.
- **Filenames don't always indicate which version is authoritative** — e.g.
  `regrid.py` vs. `finalregridalgorithm.py` vs.
  `regridvirsstartingpoint.py` implement variations of the same regridding
  step; see the stage descriptions above for which one to trust.
- A next step (not done here, since it changes code behavior rather than
  just adding scaffolding around it) would be centralizing these paths into
  one config file/CLI arguments per script, so the pipeline can be re-run
  end-to-end without manual edits. Ask for this explicitly if/when you want
  it — it touches every script.

## Version control

This repository is now tracked with git. Suggested workflow going forward:
commit after each meaningful change, use descriptive commit messages, and
avoid committing data files (already excluded via `.gitignore`).

## FAIR statement

- **Findable**: [CITATION.cff](CITATION.cff) provides machine-readable
  citation metadata; fill in the `TODO` author fields and a repository URL
  once this is hosted somewhere with a stable identifier (e.g. GitHub +
  Zenodo archive for a DOI).
- **Accessible**: [DATA_SOURCES.md](DATA_SOURCES.md) documents where each
  input dataset originates and how to obtain it; items marked TODO still
  need the original provenance filled in.
- **Interoperable**: outputs use standard formats (NetCDF/CF conventions,
  GeoDataFrame/shapefile, EPSG:4326) rather than bespoke binary formats.
- **Reusable**: [LICENSE](LICENSE) (MIT) states reuse terms;
  [requirements.txt](requirements.txt) pins the dependency set; this README
  and `DATA_SOURCES.md` describe the methodology and inputs needed to rerun
  it.

## License

MIT — see [LICENSE](LICENSE).
