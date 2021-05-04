import os
import boto3
import json


def lambda_handler(event, context):

    # show the event
    print("event", event)
    # get buckets to empty
    buckets = json.loads(os.environ["BUCKETS"])

    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception(f"Invalid request type: {request_type}")


def on_create(event):
    # get the kafka and aes security group ids
    response = {"PhysicalResourceId": "mskAttributes", "Data": {}}
    return response


def on_update(event):
    return on_create(event)


def on_delete(event):
    pass