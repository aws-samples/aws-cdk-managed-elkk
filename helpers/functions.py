# modules
import os
import boto3
from botocore.exceptions import ClientError
from helpers.constants import constants
from pathlib import Path
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
)

# set boto3 client for amazon managged kafka
kafkaclient = boto3.client("kafka")
# set the boto3 client for amazon elasticsearch
esclient = boto3.client("es")
# set the boto3 client for amazon iam
iamclient = boto3.client("iam")
# set the client for logs
logs_client = boto3.client("logs")

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


def ensure_service_linked_role(service_name: str):
    """ create the serviced linked role if it doesn't exist for a service """
    try:
        iamclient.create_service_linked_role(AWSServiceName=service_name)
    except ClientError as err:
        if (
            err.response["Error"]["Code"] == "InvalidInput"
            and "has been taken in this account" in err.response["Error"]["Message"]
        ):
            return 0
        else:
            print(f"Unexpectedd error: {err}")
            return 1
    return 0


def kafka_get_arn() -> str:
    """ get the arn for the kakfa cluster startingwith elkk- """
    kafka_clusters = kafkaclient.list_clusters()
    try:
        return [
            clstr["ClusterArn"]
            for clstr in kafka_clusters["ClusterInfoList"]
            if clstr["Tags"]["project"] == constants["PROJECT_TAG"]
        ][0]
    except IndexError:
        return ""


def kafka_get_brokers() -> str:
    """ get msk brokers from the kafka arn """
    try:
        kafka_brokers = kafkaclient.get_bootstrap_brokers(ClusterArn=kafka_get_arn())
        return kafka_brokers["BootstrapBrokerString"]
    except ClientError as err:
        if (
            err.response["Error"]["Message"]
            == "Missing required request parameters: [clusterArn]"
        ):
            return ""
        else:
            print(f"Unexpectedd error: {err}")
    return ""


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
            if "elkk-" in dom["DomainName"]
        ][0]
    except IndexError:
        return ""


def elastic_get_endpoint() -> str:
    """ get elastic endpoint using elastic domain """
    es_endpoint = esclient.describe_elasticsearch_domain(
        DomainName=elastic_get_domain()
    )
    es_endpoint = es_endpoint["DomainStatus"]["Endpoints"]["vpc"]


def update_kafka_configuration(config_file):
    """ ensure the configuration has auto enable topic """
    # check if config exists
    try:
        config_arn = [
            config
            for config in kafkaclient.list_configurations()["Configurations"]
            if config["Name"] == constants["PROJECT_TAG"]
        ][0]["Arn"]
    except IndexError as err:
        # create the config if it does not exist
        config_arn = kafkaclient.create_configuration(
            Description="Elkk Configuration",
            KafkaVersions=[constants["KAFKA_VERSION"]],
            Name=constants["PROJECT_TAG"],
            ServerProperties=Path("kafka/configuration.txt").read_text(),
        )["Arn"]
    try:
        # check the config arn attached to the cluster
        kafka_config_arn = kafkaclient.describe_cluster(ClusterArn=kafka_get_arn())[
            "ClusterInfo"
        ]["CurrentBrokerSoftwareInfo"]["ConfigurationArn"]
    except KeyError as err:
        # if not found then must be using default, get cluster version
        kafka_cluster_version = kafkaclient.describe_cluster(
            ClusterArn=kafka_get_arn()
        )["ClusterInfo"]["CurrentVersion"]
        # update cluster with configuration
        return kafka_get_arn()
        # park this for now
        try:
            kafkaclient.update_cluster_configuration(
                ClusterArn=kafka_get_arn(),
                ConfigurationInfo={"Arn": kafka_config_arn, "Revision": 1},
                CurrentVersion=kafka_cluster_version,
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "BadRequestException":
                pass
            else:
                print(f"Unexpectedd error: {err}")
    return kafka_get_arn()


def user_data_init(log_group_name: str = None):
    """ create userdata and defaults to a userdata item """
    new_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
    new_userdata.add_commands(
        # update packages
        "yum update -y",
        # add the aws logs
        "yum install -y awslogs",
        # update log group
        f"sed -i 's#log_group_name = /var/log/messages#log_group_name = {log_group_name}#' /etc/awslogs/awslogs.conf",
        # start the awslogs
        "systemctl start awslogsd",
        # set cli default region
        f"sudo -u ec2-user aws configure set region {core.Aws.REGION}",
    )
    return new_userdata


def instance_add_log_permissions(the_instance):
    """ add log permissions to an instance """
    # create policies for logs
    logs_policy = iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:DescribeLogStreams",
        ],
        resources=["*"],
    )
    # add policy to instance
    the_instance.add_to_role_policy(statement=logs_policy)


def get_log_group_arn(log_group_name):
    """ get it if exists """
    # search for log group
    log_groups = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)[
        "logGroups"
    ]
    try:
        # return the log group arn
        return [lg["arn"] for lg in log_groups][0]
    except IndexError:
        # not found
        pass
    return None