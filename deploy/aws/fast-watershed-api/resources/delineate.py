import json

from fastws.watershed import delineate


def handler(event, context):
    body = json.loads(event["body"])

    x, y, geo = delineate(
        body["streams"], body["direction"], body["x"], body["y"], body["crs"]
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"x": x, "y": y, "geo": geo}),
    }
