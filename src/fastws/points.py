"""Generate a watersheds polygon file from a vector file of points"""

from typing import Optional

import fiona
import rasterio
from pyproj import Transformer

from fastws.watershed import delineate


def delineate_watersheds(
    src: str,
    dst: str,
    streams: str,
    flow_direction: str,
    snap: bool = True,
    flow_accumulation: Optional[str] = None,
):
    """Delineate watersheds for input points and write polygon features.

    Input points are transformed to the CRS of the input rasters before
    delineation. Output geometry and snapped coordinates are written in the
    raster CRS.

    Args:
        src (str): Input point vector source path.
        dst (str): Output vector path for watershed polygons.
        streams (str): Stream raster path.
        flow_direction (str): Flow-direction raster path.
        snap (bool, optional): Whether to snap points downslope to a stream.
            Defaults to True.
        flow_accumulation (Optional[str], optional): Flow-accumulation raster path,
            required when ``snap`` is True.

    Returns:
        None: Watershed features are written to ``dst``.

    Raises:
        ValueError: If snapping is enabled without flow-accumulation input.
        ValueError: If the source layer does not contain point geometries.
        ValueError: If raster CRS metadata is missing or rasters use different CRS.
    """
    if snap and flow_accumulation is None:
        raise ValueError("Flow accumulation data must be provided when snapping")

    with rasterio.open(streams) as streams_ds, rasterio.open(flow_direction) as fd_ds:
        streams_crs = streams_ds.crs
        fd_crs = fd_ds.crs

    if streams_crs is None or fd_crs is None:
        raise ValueError(
            "Input rasters must define a valid coordinate reference system"
        )

    if streams_crs != fd_crs:
        raise ValueError("Streams and flow-direction rasters must use the same CRS")

    with fiona.open(src) as layer:
        schema = layer.schema
        crs = layer.crs

        if schema is None or schema["geometry"] != "Point":
            raise ValueError("Input vector file must have a Point geometry type")

        points = [
            {"coords": feature.geometry.coordinates, "properties": feature.properties}
            for feature in layer
            if feature.geometry is not None
        ]

    to_raster_crs = None
    if crs is not None and crs != fd_crs:
        to_raster_crs = Transformer.from_crs(crs, fd_crs, always_xy=True)

    with fiona.open(
        dst,
        "w",
        crs=fd_crs,
        schema={
            "geometry": "MultiPolygon",
            "properties": dict(schema["properties"])
            | {
                "fastws_snap_x": "float",
                "fastws_snap_y": "float",
                "fastws_area": "float",
            },
        },
    ) as layer:
        for point in points:
            point_x, point_y = point["coords"]
            if to_raster_crs is not None:
                point_x, point_y = to_raster_crs.transform(point_x, point_y)

            x, y, area, geo = delineate(
                point_x,
                point_y,
                streams,
                flow_direction,
                snap=snap,
                fa_src=flow_accumulation,
                xy_srs=fd_crs,
                out_crs=fd_crs,
            )

            layer.write({
                "geometry": geo,
                "properties": dict(point["properties"])
                | {"fastws_snap_x": x, "fastws_snap_y": y, "fastws_area": area},
            })
