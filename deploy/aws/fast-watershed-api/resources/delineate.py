from fastws.watershed import delineate


def handler(event, context):
    x, y, geo = delineate(
        event["streams"], event["direction"], event["x"], event["y"], event["crs"]
    )

    return {
        "x": x,
        "y": y,
        "geo": geo
    }
