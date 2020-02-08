# import modules
import os.path
import urllib.request

from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
)
import boto3
from elk_stack.helpers import file_updated
from elk_stack.constants import (
    ELK_PROJECT_TAG,
    ELK_KEY_PAIR,
    ELK_FILEBEAT_INSTANCE,
    ELK_TOPIC,
)

dirname = os.path.dirname(__file__)
external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class FilebeatStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, my_vpc, my_sg, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # assets for filebeat
        filebeat_sh = assets.Asset(
            self, "filebeat_sh", path=os.path.join(dirname, "filebeat.sh")
        )
        # get kakfa brokers
        kafkaclient = boto3.client("kafka")
        kafka_clusters = kafkaclient.list_clusters()
        try:
            kafka_arn = [
                kc["ClusterArn"]
                for kc in kafka_clusters["ClusterInfoList"]
                if "elk-" in kc["ClusterName"]
            ][0]
            kafka_brokers = kafkaclient.get_bootstrap_brokers(ClusterArn=kafka_arn)
            kafka_brokers = kafka_brokers["BootstrapBrokerString"]
            kafka_brokers = f'''"{kafka_brokers.replace(",", '", "')}"'''
        except IndexError:
            kafka_brokers = ""
        # update filebeat.yml to .asset
        filebeat_yml_asset = file_updated(
            os.path.join(dirname, "filebeat.yml"),
            {"$kafka_brokers": kafka_brokers, "$elk_topic": ELK_TOPIC,},
        )
        filebeat_yml = assets.Asset(self, "filebeat_yml", path=filebeat_yml_asset)
        elastic_repo = assets.Asset(
            self, "elastic_repo", path=os.path.join(dirname, "elastic.repo")
        )

        # userdata for filebeat
        fb_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
        fb_userdata.add_commands(
            "set -e",
            # get setup assets files
            f"""aws s3 cp s3://{filebeat_sh.s3_bucket_name}/{filebeat_sh.s3_object_key} /home/ec2-user/filebeat.sh""",
            f"""aws s3 cp s3://{filebeat_yml.s3_bucket_name}/{filebeat_yml.s3_object_key} /home/ec2-user/filebeat.yml""",
            f"""aws s3 cp s3://{elastic_repo.s3_bucket_name}/{elastic_repo.s3_object_key} /home/ec2-user/elastic.repo""",
            # make script executable
            "chmod +x /home/ec2-user/filebeat.sh",
            # run setup script
            ". /home/ec2-user/filebeat.sh",
        )

        # instance for filebeat
        fb_instance = ec2.Instance(
            self,
            "filebeat_client",
            instance_type=ec2.InstanceType(ELK_FILEBEAT_INSTANCE),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            vpc=my_vpc,
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            user_data=fb_userdata,
            key_name=ELK_KEY_PAIR,
            security_group=my_sg,
        )
        core.Tag.add(fb_instance, "project", ELK_PROJECT_TAG)
        # create policies for ec2 to connect to kafka
        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["kafka:ListClusters", "kafka:GetBootstrapBrokers",],
            resources=["*"],
        )
        # add the role permissions
        fb_instance.add_to_role_policy(statement=access_kafka_policy)
        # add access to the file asset
        filebeat_sh.grant_read(fb_instance)
