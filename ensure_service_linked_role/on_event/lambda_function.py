import os
import boto3
from botocore.exceptions import ClientError
import json

client = boto3.client("iam")


def lambda_handler(event, context):

    # show the event
    print("event", event)

    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception(f"Invalid request type: {request_type}")


def on_create(event):

    print("CREATE", event)

    response = {"PhysicalResourceId": "ensureServiceLinkedRole", "Data": {}}

    """ create the serviced linked role if it doesn't exist for a service """
    try:
        client.create_service_linked_role(AWSServiceName=os.environ["SERVICE"])
    except ClientError as err:
        if (
            err.response["Error"]["Code"] == "InvalidInput"
            and "has been taken in this account" in err.response["Error"]["Message"]
        ):
            return response
        else:
            print(f"Unexpected error: {err}")
            return response
    return response


def on_update(event):
    return on_create(event)


def on_delete(event):
    pass