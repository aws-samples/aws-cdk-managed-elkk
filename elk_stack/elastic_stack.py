# import modules
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_elasticsearch as aes,
    aws_iam as iam,
    aws_s3_assets as assets,
)
import os
from elk_stack.constants import (
    ELK_PROJECT_TAG,
    ELK_KEY_PAIR,
    ELK_ELASTIC_CLIENT_INSTANCE,
    ELK_ELASTIC_MASTER_COUNT,
    ELK_ELASTIC_MASTER_INSTANCE,
    ELK_ELASTIC_INSTANCE_COUNT,
    ELK_ELASTIC_INSTANCE,
    ELK_ELASTIC_VERSION
)
import urllib.request

dirname = os.path.dirname(__file__)
external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class ElasticStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        vpc_stack,
        # kafka_stack,
        client: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # assets for elastic
        elastic_sh = assets.Asset(
            self, "elastic_sh", path=os.path.join(dirname, "elastic.sh")
        )

        # security group for elastic client
        elastic_client_security_group = ec2.SecurityGroup(
            self,
            "elastic_client_security_group",
            vpc=vpc_stack.get_vpc,
            description="elastic client security group",
            allow_all_outbound=True,
        )
        core.Tag.add(elastic_client_security_group, "project", ELK_PROJECT_TAG)
        core.Tag.add(elastic_client_security_group, "Name", "elastic_client_sg")
        # Open port 22 for SSH
        elastic_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"), ec2.Port.tcp(22), "from own public ip",
        )
        # Open port for tunnel
        elastic_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"), ec2.Port.tcp(9200), "for ssh tunnel",
        )

        # security group for elastic
        elastic_security_group = ec2.SecurityGroup(
            self,
            "elastic_security_group",
            vpc=vpc_stack.get_vpc,
            description="elastic security group",
            allow_all_outbound=True,
        )
        core.Tag.add(elastic_security_group, "project", ELK_PROJECT_TAG)
        core.Tag.add(elastic_security_group, "Name", "elastic_sg")

        # ingress for elastic from self 
        elastic_security_group.connections.allow_from(
            elastic_security_group, ec2.Port.all_traffic(), "within elastic",
        )
        # ingress for elastic from elastic client
        elastic_security_group.connections.allow_from(
            elastic_client_security_group, ec2.Port.all_traffic(), "from elastic client",
        )
        # ingress for elastic client from elastic
        elastic_client_security_group.connections.allow_from(
            elastic_security_group, ec2.Port.all_traffic(), "from elastic",
        )

        # elastic policy
        elastic_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW, actions=["es:*",], resources=["*"],
        )
        elastic_policy.add_any_principal()
        elastic_document = iam.PolicyDocument()
        elastic_document.add_statements(elastic_policy)

        # create the elastic cluster
        elastic_domain = aes.CfnDomain(
            self,
            "elastic_domain",
            elasticsearch_cluster_config={
                "dedicatedMasterCount": ELK_ELASTIC_MASTER_COUNT,
                "dedicatedMasterEnabled": True,
                "dedicatedMasterType": ELK_ELASTIC_MASTER_INSTANCE,
                "instanceCount": ELK_ELASTIC_INSTANCE_COUNT,
                "instanceType": ELK_ELASTIC_INSTANCE,
                "zoneAwarenessConfig": {"availabilityZoneCount": 3},
                "zoneAwarenessEnabled": True,
            },
            elasticsearch_version=ELK_ELASTIC_VERSION,
            ebs_options={"ebsEnabled": True, "volumeSize": 10},
            vpc_options={
                "securityGroupIds": [elastic_security_group.security_group_id],
                "subnetIds": vpc_stack.get_vpc_private_subnet_ids
            },
            access_policies=elastic_document,
        )
        core.Tag.add(elastic_domain, "project", ELK_PROJECT_TAG)

        # userdata for kafka client
        elastic_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
        elastic_userdata.add_commands(
            "set -e",
            # get setup assets files
            f"""aws s3 cp s3://{elastic_sh.s3_bucket_name}/{elastic_sh.s3_object_key} /home/ec2-user/elastic.sh""",
            # make script executable
            "chmod +x /home/ec2-user/elastic.sh",
            # run setup script
            ". /home/ec2-user/elastic.sh",
        )

        # instance for testing elasticsearch
        if client == True:
            elastic_instance = ec2.Instance(
                self,
                "elastic_client",
                instance_type=ec2.InstanceType(ELK_ELASTIC_CLIENT_INSTANCE),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
                vpc=vpc_stack.get_vpc,
                vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                user_data=elastic_userdata,
                key_name=ELK_KEY_PAIR,
                security_group=elastic_client_security_group,
            )
            core.Tag.add(elastic_instance, "project", ELK_PROJECT_TAG)
            # needs kafka cluster to be available
            elastic_instance.node.add_dependency(elastic_domain)
            # add access to the file asset
            elastic_sh.grant_read(elastic_instance)
            # create policies for ec2 to connect to kafka
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
            elastic_instance.add_to_role_policy(statement=access_elastic_policy)
