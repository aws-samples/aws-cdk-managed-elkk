import os
import boto3
import json


def lambda_handler(event, context):

    # show the event
    print("event", event)
    # get buckets to empty
    buckets = json.loads(os.environ["BUCKETS"])

    for bucket in buckets:
        bkt = boto3.resource('s3').Bucket(bucket)
        print([obj for ojb in bkt.objects.all()])

    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception("Invalid request type: %s" % request_type)


def on_create(event):
    # create has nothing to do
    return { 'IsComplete': True }


def on_update(event):
    # update has nothing to do
    return { 'IsComplete': True }

def on_delete(event):
    # delete check buckets are empty
    physical_id = event["PhysicalResourceId"]
    print(f"Delete resource {physical_id}")

    # get buckets to empty
    buckets = json.loads(os.environ["BUCKETS"])

    for bucket in buckets:
        bkt = boto3.resource("s3").Bucket(bucket)
        print([obj for ojb in bkt.objects.all()])

    return { 'IsComplete': True }