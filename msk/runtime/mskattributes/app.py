import os
import logging
import boto3

kafkaclient = boto3.client("kafka")

# set the logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handler(event, context):

    # show the event
    logger.info("event")
    logger.info(event)

    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception(f"Invalid request type: {request_type}")


def on_create(event):

    # initialize response
    response = {"PhysicalResourceId": "mskAttributes", "Data": {}}

    # get the arn for the kafka cluster
    msk_info = kafkaclient.list_clusters(ClusterNameFilter=os.environ["CLUSTER_NAME"])[
        "ClusterInfoList"
    ][0]
    logger.debug("msk_info")
    logger.debug(msk_info)

    msk_arn = msk_info["ClusterArn"]
    response["Data"]["msk_arn"] = msk_arn
    logger.debug("msk_arn")
    logger.debug(msk_arn)

    msk_zookeeper = msk_info["ZookeeperConnectString"]
    response["Data"]["msk_zookeeper"] = msk_zookeeper
    logger.debug("msk_zookeeper")
    logger.debug(msk_zookeeper)

    # get the bootstrap brokers
    msk_brokers = kafkaclient.get_bootstrap_brokers(ClusterArn=msk_arn)
    for broker_string in [
        "BootstrapBrokerString",
        "BootstrapBrokerStringTls",
        "BootstrapBrokerStringSaslScram",
        "BootstrapBrokerStringSaslIam",
        "BootstrapBrokerStringPublicTls",
        "BootstrapBrokerStringPublicSaslScram",
        "BootstrapBrokerStringPublicSaslIam",
    ]:
        try:
            response["Data"]["msk_brokers"] = msk_brokers[broker_string]
            logger.info(f"{broker_string} BrokerString found")
            logger.debug(msk_brokers[broker_string])
            break
        except KeyError:
            logger.warning(f"{broker_string} BrokerString not found")

    logger.debug("msk_brokers")
    logger.debug(msk_brokers)

    return response


def on_update(event):
    return on_create(event)


def on_delete(event):
    pass
