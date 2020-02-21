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
    def __init__(
        self, scope: core.Construct, id: str, vpc_stack, kafka_stack, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # log generator asset
        log_generator_py = assets.Asset(
            self, "log_generator", path=os.path.join(dirname, "log_generator.py")
        )
        # log generator requirements.txt asset
        log_generator_requirements_txt = assets.Asset(
            self,
            "log_generator_requirements_txt",
            path=os.path.join(dirname, "log_generator_requirements.txt"),
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

        # instance for filebeat
        fb_instance = ec2.Instance(
            self,
            "filebeat_client",
            instance_type=ec2.InstanceType(ELK_FILEBEAT_INSTANCE),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            vpc=vpc_stack.get_vpc,
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            key_name=ELK_KEY_PAIR,
            security_group=kafka_stack.get_kafka_client_security_group,
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
        filebeat_yml.grant_read(fb_instance)
        elastic_repo.grant_read(fb_instance)
        log_generator_py.grant_read(fb_instance)
        log_generator_requirements_txt.grant_read(fb_instance)
        # userdata for filebeat
        fb_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
        fb_userdata.add_commands(
            # get setup assets files
            f"aws s3 cp s3://{filebeat_yml.s3_bucket_name}/{filebeat_yml.s3_object_key} /home/ec2-user/filebeat.yml",
            f"aws s3 cp s3://{elastic_repo.s3_bucket_name}/{elastic_repo.s3_object_key} /home/ec2-user/elastic.repo",
            f"aws s3 cp s3://{log_generator_py.s3_bucket_name}/{log_generator_py.s3_object_key} /home/ec2-user/log_generator.py",
            f"aws s3 cp s3://{log_generator_requirements_txt.s3_bucket_name}/{log_generator_requirements_txt.s3_object_key} /home/ec2-user/requirements.txt",
            # update packages
            "yum update -y",
            # set region region as env variable
            f'echo "export AWS_DEFAULT_REGION={core.Aws.REGION}" >> /etc/profile',
            # get python3
            "yum install python3 -y",
            # get pip
            "yum install python-pip -y",
            # make log generator executable
            "chmod +x /home/ec2-user/log_generator.py",
            # get log generator requirements
            "python3 -m pip install -r /home/ec2-user/requirements.txt",
            # filebeat
            "rpm --import https://packages.elastic.co/GPG-KEY-elasticsearch",
            # move filebeat repo file
            "mv -f /home/ec2-user/elastic.repo /etc/yum.repos.d/elastic.repo",
            # install filebeat
            "yum install filebeat -y",
            # move filebeat.yml to final location
            "mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml",
            # update log generator ownership
            "chown -R ec2-user:ec2-user /home/ec2-user",
            # start filebeat
            "systemctl start filebeat",
            # send the cfn signal
            f"/opt/aws/bin/cfn-signal --resource {fb_instance.instance.logical_id} --stack {core.Aws.STACK_NAME}",
        )
        # attach the userdata
        fb_instance.add_user_data(fb_userdata.render())
        # add creation policy for instance
        fb_instance.instance.cfn_options.creation_policy = core.CfnCreationPolicy(
            resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
        )
