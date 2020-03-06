# modules
import os
import boto3
from helpers.constants import constants

# set boto3 client for amazon managged kafka
kafkaclient = boto3.client("kafka")
# set the boto3 client for amazon elasticsearch
esclient = boto3.client("es")

# helper to create updated assets
def file_updated(file_name: str = "", updates: dict = {}):
    # read in the original file
    with open(file_name, "r") as f:
        filedata = f.read()
    # replace each key found with its value
    for key, value in updates.items():
        if value != "":
            filedata = filedata.replace(key, value)
    # save temp version of the file
    with open(f"{file_name}.asset", "w") as f:
        f.write(filedata)
    # return name of updated file
    return f"{file_name}.asset"


def kafka_get_arn() -> str:
    """ get the arn for the kakfa cluster startingwith elk- """
    kafka_clusters = kafkaclient.list_clusters()
    try:
        return [
            clstr["ClusterArn"]
            for clstr in kafka_clusters["ClusterInfoList"]
            if clstr["Tags"]["project"] == constants["ELK_PROJECT_TAG"]
        ][0]
    except IndexError:
        return ""


def kafka_get_brokers() -> str:
    """ get msk brokers from the kafka arn """
    kafka_brokers = kafkaclient.get_bootstrap_brokers(ClusterArn=kafka_get_arn())
    return kafka_brokers["BootstrapBrokerString"]
    # return f'''"{kafka_brokers.replace(",", '", "')}"'''


def elastic_get_arn() -> str:
    """ get the elastic domain using the project tag """
    pass


def elastic_get_domain() -> str:
    """ get elastic domain using the project tag """
    es_domains = esclient.list_domain_names()
    try:
        return [
            dom["DomainName"]
            for dom in es_domains["DomainNames"]
            if "elk-" in dom["DomainName"]
        ][0]
    except IndexError:
        return ""


def elastic_get_endpoint() -> str:
    """ get elastic endpoint using elastic domain """
    es_endpoint = esclient.describe_elasticsearch_domain(
        DomainName=elastic_get_domain()
    )
    es_endpoint = es_endpoint["DomainStatus"]["Endpoints"]["vpc"]
