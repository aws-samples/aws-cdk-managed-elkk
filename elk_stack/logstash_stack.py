# import modules
import os
import urllib.request
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_s3_assets as assets,
    aws_iam as iam,
    aws_cloudformation as cfn,
)
from elk_stack.constants import (
    ELK_PROJECT_TAG,
    ELK_KEY_PAIR,
    ELK_LOGSTASH_S3,
    ELK_REGION,
    ELK_TOPIC,
    ELK_LOGSTASH_INSTANCE,
)
from elk_stack.helpers import file_updated
import boto3
from botocore.exceptions import ClientError

dirname = os.path.dirname(__file__)
external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class LogstashStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc_stack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # get s3 bucket name
        s3client = boto3.client("s3")
        s3_bucket_list = s3client.list_buckets()
        try:
            s3_bucket_name = [
                bkt["Name"]
                for bkt in s3_bucket_list["Buckets"]
                if "elk-athena-" in bkt["Name"]
            ][0]
        except IndexError:
            s3_bucket_name = ""

        # get elastic endpoint
        esclient = boto3.client("es")
        es_domains = esclient.list_domain_names()
        try:
            es_domain = [
                dom["DomainName"]
                for dom in es_domains["DomainNames"]
                if "elk-" in dom["DomainName"]
            ][0]
            es_endpoint = esclient.describe_elasticsearch_domain(DomainName=es_domain)
            es_endpoint = es_endpoint["DomainStatus"]["Endpoints"]["vpc"]
        except IndexError:
            es_endpoint = ""

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
        except IndexError:
            kafka_brokers = ""

        # assets for logstash
        logstash_sh = assets.Asset(
            self, "logstash_sh", path=os.path.join(dirname, "logstash.sh")
        )
        logstash_yml = assets.Asset(
            self, "logstash_yml", path=os.path.join(dirname, "logstash.yml")
        )
        logstash_repo = assets.Asset(
            self, "logstash_repo", path=os.path.join(dirname, "logstash.repo")
        )
        # update conf file to .asset
        logstash_conf_asset = file_updated(
            os.path.join(dirname, "logstash.conf"),
            {
                "$s3_bucket": s3_bucket_name,
                "$es_endpoint": es_endpoint,
                "$kafka_brokers": kafka_brokers,
                "$elk_region": ELK_REGION,
                "$elk_topic": ELK_TOPIC,
            },
        )
        logstash_conf = assets.Asset(self, "logstash.conf", path=logstash_conf_asset,)

        # userdata for logstash
        logstash_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
        logstash_userdata.add_commands(
            "set -e",
            # get setup assets files
            f"""aws s3 cp s3://{logstash_sh.s3_bucket_name}/{logstash_sh.s3_object_key} /home/ec2-user/logstash.sh""",
            f"""aws s3 cp s3://{logstash_yml.s3_bucket_name}/{logstash_yml.s3_object_key} /home/ec2-user/logstash.yml""",
            f"""aws s3 cp s3://{logstash_repo.s3_bucket_name}/{logstash_repo.s3_object_key} /home/ec2-user/logstash.repo""",
            f"""aws s3 cp s3://{logstash_conf.s3_bucket_name}/{logstash_conf.s3_object_key} /home/ec2-user/logstash.conf""",
            # make script executable
            "chmod +x /home/ec2-user/logstash.sh",
            # run setup script
            ". /home/ec2-user/logstash.sh",
        )

        # logstash security group
        logstash_security_group = ec2.SecurityGroup(
            self,
            "logstash_security_group",
            vpc=vpc_stack.get_vpc,
            description="logstash security group",
            allow_all_outbound=True,
        )
        core.Tag.add(logstash_security_group, "project", ELK_PROJECT_TAG)
        core.Tag.add(logstash_security_group, "Name", "logstash_sg")
        # Open port 22 for SSH
        logstash_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"), ec2.Port.tcp(22), "from own public ip",
        )

        # get security group for kafka 
        ec2client = boto3.client("ec2")
        security_groups = ec2client.describe_security_groups(
            Filters=[{"Name": "tag-value", "Values": [ELK_PROJECT_TAG,]},],
        )
        kafka_sg_id = [
            sg["GroupId"]
            for sg in security_groups["SecurityGroups"]
            if "kafka security group" in sg["Description"]
        ][0]
        kafka_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "kafka_security_group", security_group_id=kafka_sg_id
        )
        # let in logstash
        kafka_security_group.connections.allow_from(
            logstash_security_group, ec2.Port.all_traffic(), "from logstash",
        )
        # get security group for elastic
        elastic_sg_id = [
            sg["GroupId"]
            for sg in security_groups["SecurityGroups"]
            if "elastic security group" in sg["Description"]
        ][0]
        elastic_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "elastic_security_group", security_group_id=elastic_sg_id
        )
        # let in logstash
        elastic_security_group.connections.allow_from(
            logstash_security_group, ec2.Port.all_traffic(), "from logstash",
        )

        # create the logstash instance
        logstash_instance = ec2.Instance(
            self,
            "logstash_client",
            instance_type=ec2.InstanceType(ELK_LOGSTASH_INSTANCE),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            vpc=vpc_stack.get_vpc,
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            user_data=logstash_userdata,
            key_name=ELK_KEY_PAIR,
            security_group=logstash_security_group,
        )
        core.Tag.add(logstash_instance, "project", ELK_PROJECT_TAG)
        # add access to the file asset
        logstash_sh.grant_read(logstash_instance)
        # create policies for logstash
        access_elastic_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "es:ListDomainNames",
                "es:DescribeElasticsearchDomain",
                "es:ESHttpPut",
            ],
            resources=["*"],
        )
        # add the role permissions
        logstash_instance.add_to_role_policy(statement=access_elastic_policy)
        # kafka policy
        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["kafka:ListClusters", "kafka:GetBootstrapBrokers",],
            resources=["*"],
        )
        logstash_instance.add_to_role_policy(statement=access_kafka_policy)
        # s3 policy
        access_s3_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW, actions=["s3:*",], resources=["*"],
        )
        logstash_instance.add_to_role_policy(statement=access_s3_policy)
