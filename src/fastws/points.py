"""Generate a watersheds polygon file from a vector file of points"""

from typing import Optional

try:
    import fiona
except ImportError:
    raise ImportError("The fiona package is required to use the `points` module.")

from fastws.watershed import delineate


def delineate_watersheds(
    src: str,
    dst: str,
    streams: str,
    flow_direction: str,
    snap: bool = True,
    flow_accumulation: Optional[str] = None,
):
    if snap and flow_accumulation is None:
        raise ValueError("Flow accumulation data must be provided when snapping")

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

    with fiona.open(
        dst,
        "w",
        crs=crs,
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
            x, y, area, geo = delineate(
                point["coords"][0],
                point["coords"][1],
                streams,
                flow_direction,
                snap=snap,
                fa_src=flow_accumulation,
                xy_srs=crs,
            )

            layer.write(
                {
                    "geometry": geo,
                    "properties": dict(point["properties"])
                    | {"fastws_snap_x": x, "fastws_snap_y": y, "fastws_area": area},
                }
            )
