# Fast Watershed

A Python package that quickly and efficiently delineates watersheds using a GRASS-derived
flow direction grid.

## Requirements

Runtime dependencies (installed automatically):

* [numpy](https://numpy.org)
* [rasterio](https://rasterio.readthedocs.io)
* [shapely](https://shapely.readthedocs.io)
* [pyproj](https://pyproj4.github.io/pyproj)

Build-time dependencies (required before installing):

* [numba](https://numba.pydata.org) — used to compile performance-critical code ahead of time
* [setuptools](https://setuptools.pypa.io)

Optional dependencies:

* [fiona](https://fiona.readthedocs.io) — required only for the `points` module (batch delineation from a vector file)
* [GRASS GIS](https://grass.osgeo.org) + [hydro-tools](https://github.com/bluegeo/hydro-tools) (+ dask, pulled by hydro-tools) — required only for the `data` module (DEM preparation)

## Installation

Because some internals are compiled ahead-of-time with numba, `setuptools` and `numba`
must be present **before** installing the package, and pip's build isolation must be
disabled:

```bash
pip install setuptools numba
pip install --no-build-isolation .
```

## Data Preparation

The `data` module generates the flow direction, flow accumulation, and stream rasters
required by the delineation functions. It depends on:

1. [GRASS GIS](https://grass.osgeo.org) installed on the system
2. [hydro-tools](https://github.com/bluegeo/hydro-tools):

```bash
pip install git+https://github.com/bluegeo/hydro-tools.git
```

### Prepare grids from a DEM

```python
from fastws.data import prepare_data

prepare_data("/path/to/dem.tif")
```

Three GeoTIFFs are written to the same directory as the DEM:

| File | Description |
|------|-------------|
| `<dem>_flow_dir_native.tif` | GRASS D8 flow direction |
| `<dem>_flow_acc_native.tif` | Flow accumulation (masked to stream cells) |
| `<dem>_streams_native.tif` | Stream network |

When `resolutions` are provided, the suffix `native` is replaced with the resolution
value (e.g. `_flow_dir_25.tif`):

```python
prepare_data("/path/to/dem.tif", resolutions=[15, 25, 50, 100, 200])
```

## Raster Requirements and Assumptions

`fastws` expects raster inputs to meet these conditions:

* Inputs must be **tiled** GeoTIFFs (non-tiled rasters raise `ValueError: Input raster should be tiled`)
* `stream_src`, `fd_src`, and `fa_src` should use the same grid definition (extent, resolution, and CRS)
* Flow direction values are expected to use GRASS D8 encoding (`1..8`), with values `<= 0` treated as no-flow/off-map
* Stream cells are identified as values that are not the stream raster `nodata`

## Delineating a Watershed

### Basic usage

```python
from fastws.watershed import delineate

x, y, area, geo = delineate(
    x,
    y,
    "/path/to/streams.tif",
    "/path/to/flow_dir.tif",
)
```

### Finding the nearest stream first

Use `find_stream` to move an outlet point downslope to the nearest stream and get
its upstream accumulation area:

```python
from fastws.watershed import find_stream

x, y, accum_area = find_stream(
    "/path/to/streams.tif",
    "/path/to/flow_dir.tif",
    "/path/to/flow_acc.tif",
    x,
    y,
)
```

`delineate` returns four values:

| Return value | Description |
|--------------|-------------|
| `x` | X-coordinate of the outlet (may differ from the input if `snap=True`) |
| `y` | Y-coordinate of the outlet (may differ from the input if `snap=True`) |
| `area` | Watershed area in the units of the raster CRS |
| `geo` | GeoJSON `MultiPolygon` of the watershed boundary |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `x` | `float` | — | X-coordinate of the outlet point |
| `y` | `float` | — | Y-coordinate of the outlet point |
| `stream_src` | `str` | — | Path to the stream raster |
| `fd_src` | `str` | — | Path to the flow direction raster |
| `xy_srs` | `str \| int` | `None` | CRS of the input point (EPSG, WKT, or PROJ4). Defaults to the raster CRS |
| `snap` | `bool` | `False` | Move the point downslope until it reaches a stream cell. Requires `fa_src` |
| `fa_src` | `str` | `None` | Path to the flow accumulation raster. Required when `snap=True` |
| `out_crs` | `str \| int` | `None` | CRS for the output polygon. Defaults to the raster CRS |
| `simplify` | `float` | `0` | Simplify the output geometry with this tolerance (0 = no simplification) |
| `smooth` | `float` | `0` | Smooth the output geometry with this buffer distance (0 = no smoothing) |
| `upstream_offset` | `list[int, int]` | `None` | Row/column offset of the upstream cell to use at a confluence, to avoid including all tributaries |

### Snapping to a stream

When the input point is not exactly on a stream cell, set `snap=True` and provide the
flow accumulation raster. The point is moved downslope until it hits a stream:

```python
x, y, area, geo = delineate(
    x,
    y,
    "/path/to/streams.tif",
    "/path/to/flow_dir.tif",
    snap=True,
    fa_src="/path/to/flow_acc.tif",
)
```

### Reprojecting input/output

Use `xy_srs` when the input point is in a different CRS than the rasters, and `out_crs`
to return the watershed polygon in a specific CRS (e.g. WGS 84):

```python
x, y, area, geo = delineate(
    -123.1207,  # longitude
    49.2827,  # latitude
    "/path/to/streams.tif",
    "/path/to/flow_dir.tif",
    xy_srs=4326,
    snap=True,
    fa_src="/path/to/flow_acc.tif",
    out_crs=4326,
)
```

`area` is always returned in the source raster CRS units, even when `out_crs` is set.

## Batch Delineation from a Points File

The `points` module delineates a watershed for every point in a vector file and writes
the results to a new polygon file. Requires [fiona](https://fiona.readthedocs.io).
The input layer geometry type must be `Point`.

```python
from fastws.points import delineate_watersheds

delineate_watersheds(
    src="/path/to/outlets.gpkg",  # input point vector
    dst="/path/to/watersheds.gpkg",  # output polygon vector
    streams="/path/to/streams.tif",
    flow_direction="/path/to/flow_dir.tif",
    snap=True,
    flow_accumulation="/path/to/flow_acc.tif",
)
```

The output file inherits all properties from the input and adds three new fields:

| Field | Description |
|-------|-------------|
| `fastws_snap_x` | Snapped outlet X-coordinate |
| `fastws_snap_y` | Snapped outlet Y-coordinate |
| `fastws_area` | Watershed area in the raster CRS units |

## Variable-Resolution Delineation

Delineating at variable resolutions improves performance at scale: use high resolution
for small watersheds and coarser resolution for large ones. Prepare the multi-resolution
grids with `prepare_data(dem, resolutions=[15, 25, 50, 100, 200])`, then:

```python
from fastws.watershed import find_stream, delineate

STREAMS_PATH = "/path/to/dem_streams_{}.tif"
DIRECTION_PATH = "/path/to/dem_flow_dir_{}.tif"
ACCUMULATION_PATH = "/path/to/dem_flow_acc_{}.tif"

X_COORD = 1.1
Y_COORD = 2.2

RESOLUTIONS = [15, 25, 50, 100, 200]
# Minimum accumulation areas (in raster CRS units²) that trigger stepping up to a coarser resolution
AREA_THRESHOLDS = [1.8e8, 5e8, 2e9, 8e9]

# Snap to the stream at the finest resolution to get the accumulation area
x, y, accum_area = find_stream(
    STREAMS_PATH.format(RESOLUTIONS[0]),
    DIRECTION_PATH.format(RESOLUTIONS[0]),
    ACCUMULATION_PATH.format(RESOLUTIONS[0]),
    X_COORD,
    Y_COORD,
)

# Pick the appropriate resolution based on the upstream area
resolution = RESOLUTIONS[
    next((i for i, a in enumerate(AREA_THRESHOLDS) if accum_area < a), -1)
]

# Delineate at the chosen resolution, snapping to account for grid differences
x, y, area, geo = delineate(
    x,
    y,
    STREAMS_PATH.format(resolution),
    DIRECTION_PATH.format(resolution),
    snap=True,
    fa_src=ACCUMULATION_PATH.format(resolution),
)
```

