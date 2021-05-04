import os
import boto3
import json

kafkaclient = boto3.client("kafka")


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

    response = {"PhysicalResourceId": "mskAttributes", "Data": {}}

    # get the arn for the kafka cluster
    msk_info = kafkaclient.list_clusters(ClusterNameFilter=os.environ["CLUSTER_NAME"])[
        "ClusterInfoList"
    ][0]
    msk_arn = msk_info["ClusterArn"]
    msk_zookeeper = msk_info["ZookeeperConnectString"]
    response["Data"]["msk_arn"] = msk_arn
    response["Data"]["msk_zookeeper"] = msk_zookeeper

    # get the bootstrap brokers
    msk_brokers = kafkaclient.get_bootstrap_brokers(ClusterArn=msk_arn)[
        "BootstrapBrokerString"
    ]
    response["Data"]["msk_brokers"] = msk_brokers

    return response


def on_update(event):
    return on_create(event)


def on_delete(event):
    pass