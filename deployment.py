from typing import Any

# cdk stuff
from constructs import Construct
from aws_cdk import Stack, Stage

# get constants
import constants

# get stacks
from vpc.infrastructure import VpcStack
from msk.infrastructure import MskCluster, KafkaClient
from filebeat.infrastructure import FilebeatStack

# from orchestration.infrastructure import MWAA
# from consume.infrastructure import Athena, Redshift, SageMaker
# from batch.infrastructure import EMR, Glue, GlueJob


class OLK(Stage):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)

        # Vpc stack
        vpcstack = VpcStack(self, "vpcstack")

        # kafka
        kafka = Stack(self, "kafka")
        # msk cluster
        mskcluster = MskCluster(
            kafka,
            "mskcluster",
            PROJECT_TAG=f"{constants.CDK_APP_NAME}-dev",
            VPC=vpcstack.VPC,
            EXTERNAL_IP=constants.EXTERNAL_IP,
            MSK_INSTANCE_TYPE=constants.MSK_INSTANCE_TYPE_DEV,
            MSK_BROKER_NODES=constants.MSK_BROKER_NODES_DEV,
            MSK_KAFKA_VERSION=constants.MSK_KAFKA_VERSION_DEV,
        )

        # kafka client instance
        kafkaclient = KafkaClient(
            kafka,
            "kafkaclient",
            KEY_PAIR=constants.KEY_PAIR_DEV,
            VPC=vpcstack.VPC,
            MSK_KAFKACLIENT_INSTANCE_TYPE=constants.MSK_KAFKACLIENT_INSTANCE_TYPE_DEV,
            MSK_KAFKACLIENT_DOWNLOAD_VERSION=constants.MSK_KAFKACLIENT_DOWNLOAD_VERSION_DEV,
            MSK_KAFKACLIENT_SECURITY_GROUP=mskcluster.MSK_KAFKACLIENT_SECURITY_GROUP,
            #MSK_BROKERS=mskcluster.MSK_BROKERS,
            #MSK_ZOOKEEPER=mskcluster.MSK_ZOOKEEPER,
            MSK_BROKERS=constants.MSK_BROKERS,
            MSK_ZOOKEEPER=constants.MSK_ZOOKEEPER,
        )

        # filebeatstack = FilebeatStack(
        #    self, "filebeatstack", MSK_BROKERS=mskstack.msk_brokers
        # )
