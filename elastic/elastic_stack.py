# import modules
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_elasticsearch as aes,
    aws_iam as iam,
    aws_s3_assets as assets,
)
import os
from helpers.constants import constants
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

        # security group for elastic client
        elastic_client_security_group = ec2.SecurityGroup(
            self,
            "elastic_client_security_group",
            vpc=vpc_stack.get_vpc,
            description="elastic client security group",
            allow_all_outbound=True,
        )
        core.Tag.add(
            elastic_client_security_group, "project", constants["ELK_PROJECT_TAG"]
        )
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
        core.Tag.add(elastic_security_group, "project", constants["ELK_PROJECT_TAG"])
        core.Tag.add(elastic_security_group, "Name", "elastic_sg")

        # ingress for elastic from self
        elastic_security_group.connections.allow_from(
            elastic_security_group, ec2.Port.all_traffic(), "within elastic",
        )
        # ingress for elastic from elastic client
        elastic_security_group.connections.allow_from(
            elastic_client_security_group,
            ec2.Port.all_traffic(),
            "from elastic client",
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
                "dedicatedMasterCount": constants["ELK_ELASTIC_MASTER_COUNT"],
                "dedicatedMasterEnabled": True,
                "dedicatedMasterType": constants["ELK_ELASTIC_MASTER_INSTANCE"],
                "instanceCount": constants["ELK_ELASTIC_INSTANCE_COUNT"],
                "instanceType": constants["ELK_ELASTIC_INSTANCE"],
                "zoneAwarenessConfig": {"availabilityZoneCount": 3},
                "zoneAwarenessEnabled": True,
            },
            elasticsearch_version=constants["ELK_ELASTIC_VERSION"],
            ebs_options={"ebsEnabled": True, "volumeSize": 10},
            vpc_options={
                "securityGroupIds": [elastic_security_group.security_group_id],
                "subnetIds": vpc_stack.get_vpc_private_subnet_ids,
            },
            access_policies=elastic_document,
        )
        core.Tag.add(elastic_domain, "project", constants["ELK_PROJECT_TAG"])

        # instance for elasticsearch
        if client == True:
            elastic_instance = ec2.Instance(
                self,
                "elastic_client",
                instance_type=ec2.InstanceType(
                    constants["ELK_ELASTIC_CLIENT_INSTANCE"]
                ),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
                vpc=vpc_stack.get_vpc,
                vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                key_name=constants["ELK_KEY_PAIR"],
                security_group=elastic_client_security_group,
            )
            core.Tag.add(elastic_instance, "project", constants["ELK_PROJECT_TAG"])
            # needs elastic domain to be available
            elastic_instance.node.add_dependency(elastic_domain)
            # create policies for ec2 to connect to elastic
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
            # userdata for elastic client
            elastic_userdata = ec2.UserData.for_linux(shebang="#!/bin/bash -xe")
            elastic_userdata.add_commands(
                # update packages
                "yum update -y",
                # set cli default region
                f"sudo -u ec2-user aws configure set region {core.Aws.REGION}",
                # send the cfn signal
                f"/opt/aws/bin/cfn-signal --resource {elastic_instance.instance.logical_id} --stack {core.Aws.STACK_NAME}",
            )
            elastic_instance.add_user_data(elastic_userdata.render())
            # add creation policy for instance
            elastic_instance.instance.cfn_options.creation_policy = core.CfnCreationPolicy(
                resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
            )
