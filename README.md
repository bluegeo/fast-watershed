# Fast Watershed

A package that quickly and efficiently delineates watersheds using a GRASS-derived
flow direction grid.

### Installation

```bash
# From the root of the directory
pip install .
```

### Data Preparation

Create flow direction and stream rasters from a DEM using GRASS GIS:

1. Generate flow accumulation using [r.watershed](https://grass.osgeo.org/grass82/manuals/r.watershed.html)
2. Use flow accumulation from step 1. and simulate stream locations and generate flow direction using [r.stream.extract](https://grass.osgeo.org/grass82/manuals/r.stream.extract.html)

Ensure that output rasters are compressed (for best performance) and tiled. The recommended
method is to save rasters as Cloud Optimized GeoTiffs, which may then be hosted on a network.

### Derive a watershed

From an (x, y) point a watershed may be derived using the following:

python```
from fastws.watershed import delineate

x, y, geo = delineate("/path/to/streams.tif", "/path/to/flow_direction.tif", x, y, crs)
```

The above will:

1. Transform the point from the spatial reference provided by the `crs` argument (which may be an EPSG, WKT, or PROJ4
string) into the same coordinate system as the raster.
2. Move the input point downslope until it encounters a stream.
3. Delineate a watershed above the point and return a GeoJSON object.

The resulting parameters are:

* `x`: An updated x coordinate that lies on a stream.
* `y`: An updated y coordinate that lies on a stream.
* `geo`: A MultiPolygon GeoJSON dictionary in WGS84 with the resulting watershed boundary.
