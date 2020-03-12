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
from helpers.functions import (
    ensure_service_linked_role,
    user_data_init,
    instance_add_log_permissions,
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

        # ensure that the service linked role exists
        ensure_service_linked_role("es.amazonaws.com")

        # security group for elastic client
        elastic_client_security_group = ec2.SecurityGroup(
            self,
            "elastic_client_security_group",
            vpc=vpc_stack.get_vpc,
            description="elastic client security group",
            allow_all_outbound=True,
        )
        core.Tag.add(elastic_client_security_group, "project", constants["PROJECT_TAG"])
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
        core.Tag.add(elastic_security_group, "project", constants["PROJECT_TAG"])
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

        # cluster config
        cluster_config = {
            "instanceCount": constants["ELASTIC_INSTANCE_COUNT"],
            "instanceType": constants["ELASTIC_INSTANCE"],
            "zoneAwarenessEnabled": True,
            "zoneAwarenessConfig": {"availabilityZoneCount": 3},
        }
        if constants["ELASTIC_DEDICATED_MASTER"] == True:
            cluster_config["dedicatedMasterEnabled"] = True
            cluster_config["dedicatedMasterType"] = constants["ELASTIC_MASTER_INSTANCE"]
            cluster_config["dedicatedMasterCount"] = constants["ELASTIC_MASTER_COUNT"]

        # create the elastic cluster
        elastic_domain = aes.CfnDomain(
            self,
            "elastic_domain",
            elasticsearch_cluster_config=cluster_config,
            elasticsearch_version=constants["ELASTIC_VERSION"],
            ebs_options={"ebsEnabled": True, "volumeSize": 10},
            vpc_options={
                "securityGroupIds": [elastic_security_group.security_group_id],
                "subnetIds": vpc_stack.get_vpc_private_subnet_ids,
            },
            access_policies=elastic_document,
        )
        core.Tag.add(elastic_domain, "project", constants["PROJECT_TAG"])

        # instance for elasticsearch
        if client == True:
            # userdata for kafka client
            elastic_userdata = user_data_init(log_group_name="elkk/elastic/instance")
            # create the instance
            elastic_instance = ec2.Instance(
                self,
                "elastic_client",
                instance_type=ec2.InstanceType(constants["ELASTIC_CLIENT_INSTANCE"]),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
                vpc=vpc_stack.get_vpc,
                vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                key_name=constants["KEY_PAIR"],
                security_group=elastic_client_security_group,
                user_data=elastic_userdata,
            )
            core.Tag.add(elastic_instance, "project", constants["PROJECT_TAG"])
            # needs elastic domain to be available
            elastic_instance.node.add_dependency(elastic_domain)
            # create policies for EC2 to connect to Elastic
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
            # add log permissions
            instance_add_log_permissions(elastic_instance)
            # add the signal
            elastic_userdata.add_signal_on_exit_command(resource=elastic_instance)
            # add creation policy for instance
            elastic_instance.instance.cfn_options.creation_policy = core.CfnCreationPolicy(
                resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
            )
