import os
import json
import traceback

from fastws.watershed import find_stream, delineate


# Path to a Streams raster
STREAMS_PATH = os.environ["STREAMS_PATH"]

# Path to a Flow Direction raster
DIRECTION_PATH = os.environ["DIRECTION_PATH"]

# Path to a flow accumulation raster (ideally limited to stream cells)
ACCUMULATION_PATH = os.environ["ACCUMULATION_PATH"]

# Resolutions hierarchy to complete delineations
RESOLUTIONS = json.loads(os.environ["RESOLUTIONS"])

# Area thresholds to constrain resolution
AREA_THRESH = json.loads(os.environ["AREA_THRESH"])


def handler(event, context):
    try:
        body = json.loads(event["body"])

        if body.get("prime", False):
            result = {"response": "success"}

        else:
            x, y, accum_area = find_stream(
                STREAMS_PATH.format(RESOLUTIONS[0]),
                DIRECTION_PATH.format(RESOLUTIONS[0]),
                ACCUMULATION_PATH.format(RESOLUTIONS[0]),
                body["x"],
                body["y"],
                body["crs"],
            )

            resolution = RESOLUTIONS[
                next((i for i, a in enumerate(AREA_THRESH) if accum_area < a), -1)
            ]

            x, y, area, geo = delineate(
                STREAMS_PATH.format(resolution),
                DIRECTION_PATH.format(resolution),
                ACCUMULATION_PATH.format(resolution),
                x,
                y,
                body["crs"],
                simplify=body.get("simplify", 0),
                smooth=body.get("smooth", 0),
            )

            result = {
                "response": "success",
                "x": x,
                "y": y,
                "res": resolution,
                "area": area,
                "geo": geo,
            }
    except:
        result = {"response": "error", "error": traceback.format_exc()}

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(result),
    }
