"""Generate a watersheds polygon file from a vector file of points
"""

import fiona

from fastws.watershed import delineate


def delineate_watersheds(
    src: str, dst: str, streams: str, flow_accumulation: str, flow_direction: str
):
    with fiona.open(src) as layer:
        schema = layer.schema
        crs = layer.crs

        if schema["geometry"] != "Point":
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
                streams,
                flow_direction,
                flow_accumulation,
                point["coords"][0],
                point["coords"][1],
                crs,
                wgs_84=False,
            )

            layer.write(
                {
                    "geometry": geo,
                    "properties": dict(point["properties"])
                    | {"snapped_x": x, "snapped_y": y, "area": area},
                }
            )
