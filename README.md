# Fast Watershed

A python package that quickly and efficiently delineates watersheds using a GRASS-derived
flow direction grid.

### Installation

The package requires numba to compile some of the code ahead of time. To achieve this,
`setuptools` and `numba` (which include `numpy`) must be installed and the package must
be installed without pip creating an isolated environment.

```bash
pip install setuptools numba
pip install --no-build-isolation .
```

### Data Preparation

To create grids from a DEM that can be used by the package the `data` module has been
provided. To use this module there are several dependencies:

1. [GRASS GIS](https://grass.osgeo.org) must be installed
2. [hydro-tools](https://github.com/bluegeo/hydro-tools) must be installed:
`pip install git+https://github.com/bluegeo/hydro-tools.git`

#### Prepare data from a DEM:

To run the preparation tool:

```python
from fastws.data import prepare_data

prepare_data(dem_path)
```

Grids of flow direction, flow accumulation, and streams will be created in
the same directory as the DEM. If `resolutions` are provided, each resolution number
is appended to the file names.

### Derive a watershed

From an (x, y) point in the same coordinate reference system as the rastrs,
a watershed may be derived like this:

```python
from fastws.watershed import delineate


x, y, area, geo = delineate(
    x,
    y,
    "/path/to/my_streams.tif",
    "/path/to/my_flow_dir.tif"
)
```

When running `delineate` x and y are returned anew because they may be modified if the
`snap` argument is set to `True` and a flow accumulation grid is included. The remaining
returned variables from above include:

* `area`, which is the watershed area in the raster crs; and
* `geo`, which is a geojson MultiPolygon with the watershed boundary in the crs
specified by the `out_crs` parameter, or the raster crs if it is not provided.

The above will:

1. Transform the point from the spatial reference provided by the `crs` argument (which may be an EPSG, WKT, or PROJ4
string) into the same coordinate system as the raster.
2. Move the input point downslope until it encounters a stream.
3. Delineate a watershed above the point and return a GeoJSON object.

The resulting parameters are:

* `x`: An updated x coordinate that lies on a stream.
* `y`: An updated y coordinate that lies on a stream.
* `area`: Resulting area of the watershed in the raster crs.
* `geo`: A MultiPolygon GeoJSON dictionary in WGS84 with the resulting watershed boundary.

### Variable-resolution delineation

Delineating using variable resolutions are useful for scale. For example, you could
use a higher resolution to delineate smaller watersheds, and larger resolutions to
delineate larger watersheds for the sake of speed.

To prepare for this you can use the `resolutions` argument in the `data` module.

To use variable resolutions in a workflow, you could do something like this:

```python
from fastws.watershed import find_stream, delineate

STEAMS_PATH = "/path/to/my_streams_{}.tif"
DIRECTION_PATH = "/path/to/my_flow_dir_{}.tif"
ACCUMULATION_PATH = "/path/to/my_flow_acc_{}.tif"

X_COORD = 1.1
Y_COORD = 2.2

RESOLUTIONS = [15, 25, 50, 100, 200]
# Minimum areas that indicate when to step up resolutions
AREA_THRESHOLDS = [1.8e8, 5e8, 2e9, 8e9]

# Start by snapping to the stream of the highest-resolution raster
# This returns the flow accumulation area, which is used in the next step
x, y, accum_area = find_stream(
    STREAMS_PATH.format(RESOLUTIONS[0]),
    DIRECTION_PATH.format(RESOLUTIONS[0]),
    ACCUMULATION_PATH.format(RESOLUTIONS[0]),
    X_COORD,
    Y_COORD
)

# Find the resolution to use
resolution = RESOLUTIONS[
    next((i for i, a in enumerate(AREA_THRESHOLDS) if accum_area < a), -1)
]

# Delineate the watershed, while snapping to ensure differences in resolution do not
# affect the outlet placements
x, y, area, geo = delineate(
    x,
    y,
    STEAMS_PATH.format(resolution),
    DIRECTION_PATH.format(resolution),
    snap=True,
    ACCUMULATION_PATH.format(resolution),
)
```

