# import modules
import os
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_s3_assets as assets,
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_cloudformation as cfn,
)
from s3_cleaner import S3Cleaner
from constants import ELK_PROJECT_TAG, ELK_KEY_PAIR

dirname = os.path.dirname(__file__)


class LogstashStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, myvpc, mymsk, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

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
        logstash_conf = assets.Asset(
            self, "logstash.conf", path=os.path.join(dirname, "logstash.conf")
        )

        # get security group from kafka
        logstash_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "logstash_security_group",
            security_group_id=mymsk.kafka_client_security_group.security_group_id,
        )

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

        # create the logstash instance
        logstash_instance = ec2.Instance(
            self,
            "logstash_client",
            instance_type=ec2.InstanceType("t2.xlarge"),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            vpc=myvpc.get_vpc(),
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            user_data=logstash_userdata,
            key_name=ELK_KEY_PAIR,
            security_group=logstash_security_group,
        )
        core.Tag.add(logstash_instance, "project", ELK_PROJECT_TAG)
        # add access to the file asset
        logstash_sh.grant_read(logstash_instance)
        # create policies for logstash
        access_logstash_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "es:ListDomainNames",
                "es:DescribeElasticsearchDomain",
                "es:ESHttpPut",
                "kafka:ListClusters",
                "kafka:GetBootstrapBrokers",
            ],
            resources=["*"],
        )
        # add the role permissions
        logstash_instance.add_to_role_policy(statement=access_logstash_policy)

        # create the s3 bucket
        logstash_s3 = s3.Bucket(self, "logstash_s3")
        core.Tag.add(logstash_s3, "project", ELK_PROJECT_TAG)

        # custom resource to invote lambda
        s3_cleaner = S3Cleaner(
            self, "s3_cleaner",
            message="CustomResource says hello",
            bucket=logstash_s3.bucket_arn
        )
        core.Tag.add(s3_cleaner, "project", ELK_PROJECT_TAG)
        s3_cleaner.node.add_dependency(logstash_s3)

