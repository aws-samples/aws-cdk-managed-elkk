# import modules
import os
import io

import boto3
from botocore.exceptions import ClientError
import urllib.request
from aws_cdk import (
    core,
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
)

kafka = boto3.client("kafka")

# get constants
from helpers.constants import constants
from helpers.functions import (
    file_updated,
    kafka_get_brokers,
    ensure_service_linked_role,
    update_kafka_configuration,
)

dirname = os.path.dirname(__file__)
external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class KafkaStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, vpc_stack, client: bool = True, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ensure that the service linked role exists
        ensure_service_linked_role("kafka.amazonaws.com")

        # create assets
        client_properties = assets.Asset(
            self, "client_properties", path=os.path.join(dirname, "client.properties")
        )

        # security group for kafka clients
        self.kafka_client_security_group = ec2.SecurityGroup(
            self,
            "kafka_client_security_group",
            vpc=vpc_stack.get_vpc,
            description="kafka client security group",
            allow_all_outbound=True,
        )
        core.Tag.add(
            self.kafka_client_security_group, "project", constants["PROJECT_TAG"]
        )
        core.Tag.add(self.kafka_client_security_group, "Name", "kafka_client_sg")

        # Open port 22 for SSH
        self.kafka_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"), ec2.Port.tcp(22), "from own public ip",
        )

        # security group for kafka
        self.kafka_security_group = ec2.SecurityGroup(
            self,
            "kafka_security_group",
            vpc=vpc_stack.get_vpc,
            description="kafka security group",
            allow_all_outbound=True,
        )
        core.Tag.add(self.kafka_security_group, "project", constants["PROJECT_TAG"])
        core.Tag.add(self.kafka_security_group, "Name", "kafka_sg")

        # add ingress for kafka security group
        self.kafka_security_group.connections.allow_from(
            self.kafka_security_group, ec2.Port.all_traffic(), "within kafka",
        )
        self.kafka_security_group.connections.allow_from(
            self.kafka_client_security_group,
            ec2.Port.all_traffic(),
            "from kafka client sg",
        )

        # ingress for kc sg
        self.kafka_client_security_group.connections.allow_from(
            self.kafka_security_group, ec2.Port.all_traffic(), "from kafka",
        )

        # create the kafka cluster
        self.kafka_cluster = msk.CfnCluster(
            self,
            "kafka_cluster",
            broker_node_group_info={
                "clientSubnets": vpc_stack.get_vpc_public_subnet_ids,
                "instanceType": constants["KAFKA_INSTANCE_TYPE"],
                "numberOfBrokerNodes": constants["KAFKA_BROKER_NODES"],
                "securityGroups": [self.kafka_security_group.security_group_id],
            },
            encryption_info={
                "encryptionInTransit": {
                    "InCluster": "true",
                    "clientBroker": "PLAINTEXT",
                },
            },
            cluster_name=constants["PROJECT_TAG"],
            kafka_version=constants["KAFKA_VERSION"],
            number_of_broker_nodes=constants["KAFKA_BROKER_NODES"],
            enhanced_monitoring="DEFAULT",
        )
        core.Tag.add(self.kafka_cluster, "project", constants["PROJECT_TAG"])

        # instance for kafka client
        if client == True:
            kafka_client_instance = ec2.Instance(
                self,
                "kafka_client",
                instance_type=ec2.InstanceType(constants["KAFKA_CLIENT_INSTANCE"]),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
                vpc=vpc_stack.get_vpc,
                vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                key_name=constants["KEY_PAIR"],
                security_group=self.kafka_client_security_group,
            )
            core.Tag.add(kafka_client_instance, "project", constants["PROJECT_TAG"])
            # needs kafka cluster to be available
            kafka_client_instance.node.add_dependency(self.kafka_cluster)
            # create policies for ec2 to connect to kafka
            access_kafka_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kafka:ListClusters",
                    "kafka:GetBootstrapBrokers",
                    "kafka:DescribeCluster",
                ],
                resources=["*"],
            )
            # add the role permissions
            kafka_client_instance.add_to_role_policy(statement=access_kafka_policy)
            # add access to the file asset
            client_properties.grant_read(kafka_client_instance)
            # userdata for kafka client
            kafka_client_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
            kafka_client_userdata.add_commands(
                # get setup assets files
                f"aws s3 cp s3://{client_properties.s3_bucket_name}/{client_properties.s3_object_key} /home/ec2-user/client.properties",
                # update packages
                "yum update -y",
                # update java
                "yum install java-1.8.0 -y",
                # set cli default region
                f"sudo -u ec2-user aws configure set region {core.Aws.REGION}",
                # install kakfa
                f'wget https://www-us.apache.org/dist/kafka/{constants["KAFKA_DOWNLOAD_VERSION"].split("-")[-1]}/{constants["KAFKA_DOWNLOAD_VERSION"]}.tgz',
                f"tar -xvf {constants['KAFKA_DOWNLOAD_VERSION']}.tgz",
                f"mv {constants['KAFKA_DOWNLOAD_VERSION']} /opt",
                f"rm {constants['KAFKA_DOWNLOAD_VERSION']}.tgz",
                # move client.properties to correct location
                f"mv -f /home/ec2-user/client.properties /opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/client.properties",
                # create the topic, if already exists capture error message
                f"kafka_arn=`aws kafka list-clusters --region {core.Aws.REGION} --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn",
                # get the zookeeper
                f"kafka_zookeeper=`aws kafka describe-cluster --cluster-arn $kafka_arn --region {core.Aws.REGION} --output text --query 'ClusterInfo.ZookeeperConnectString'` && echo $kafka_zookeeper",
                # create the topics
                f"make_topic=`/opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic {constants['ELKK_TOPIC']} 2>&1`",
                "echo $make_topic",
                # signal build is done
                f"/opt/aws/bin/cfn-signal --resource {kafka_client_instance.instance.logical_id} --stack {core.Aws.STACK_NAME}",
            )
            # attach the userdata
            kafka_client_instance.add_user_data(kafka_client_userdata.render())
            # add creation policy for instance
            kafka_client_instance.instance.cfn_options.creation_policy = core.CfnCreationPolicy(
                resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
            )

    # properties
    @property
    def get_kafka_client_security_group(self):
        return self.kafka_client_security_group
