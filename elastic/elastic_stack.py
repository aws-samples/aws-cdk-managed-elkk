# import modules
from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_elasticsearch as aes,
    aws_iam as iam,
    aws_s3_assets as assets,
    aws_logs as logs,
)
from helpers.functions import (
    ensure_service_linked_role,
    user_data_init,
    instance_add_log_permissions,
)
import urllib.request

external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class ElasticStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        vpc_stack,
        constants: dict,
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
            vpc=vpc_stack.output_props["vpc"],
            description="elastic client security group",
            allow_all_outbound=True,
        )
        core.Tags.of(elastic_client_security_group).add(
            "project", constants["PROJECT_TAG"]
        )
        core.Tags.of(elastic_client_security_group).add("Name", "elastic_client_sg")
        # Open port 22 for SSH
        elastic_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"),
            ec2.Port.tcp(22),
            "from own public ip",
        )
        # Open port for tunnel
        elastic_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"),
            ec2.Port.tcp(9200),
            "for ssh tunnel",
        )

        # security group for elastic
        elastic_security_group = ec2.SecurityGroup(
            self,
            "elastic_security_group",
            vpc=vpc_stack.output_props["vpc"],
            description="elastic security group",
            allow_all_outbound=True,
        )
        core.Tags.of(elastic_security_group).add("project", constants["PROJECT_TAG"])
        core.Tags.of(elastic_security_group).add("Name", "elastic_sg")

        # ingress for elastic from self
        elastic_security_group.connections.allow_from(
            elastic_security_group,
            ec2.Port.all_traffic(),
            "within elastic",
        )
        # ingress for elastic from elastic client
        elastic_security_group.connections.allow_from(
            elastic_client_security_group,
            ec2.Port.all_traffic(),
            "from elastic client",
        )
        # ingress for elastic client from elastic
        elastic_client_security_group.connections.allow_from(
            elastic_security_group,
            ec2.Port.all_traffic(),
            "from elastic",
        )

        # elastic policy
        elastic_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "es:*",
            ],
            resources=["*"],
        )
        elastic_policy.add_any_principal()
        elastic_document = iam.PolicyDocument()
        elastic_document.add_statements(elastic_policy)

        # create the cluster
        elastic_domain = aes.Domain(
            self,
            "elastic_domain",
            version=aes.ElasticsearchVersion.V7_9,
            capacity=aes.CapacityConfig(
                data_node_instance_type=constants["ELASTIC_INSTANCE"],
                data_nodes=constants["ELASTIC_INSTANCE_COUNT"],
                master_node_instance_type=constants["ELASTIC_MASTER_INSTANCE"],
                master_nodes=constants["ELASTIC_MASTER_COUNT"],
            ),
            removal_policy=core.RemovalPolicy.DESTROY,
            access_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountRootPrincipal()],
                    actions=[
                        "es:*",
                    ],
                    resources=["*"],
                )
            ],
            ebs=aes.EbsOptions(enabled=True, volume_size=10),
            vpc=vpc_stack.output_props["vpc"],
            vpc_subnets=[
                ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True)
            ],
            zone_awareness=aes.ZoneAwarenessConfig(
                availability_zone_count=3, enabled=True
            ),
            security_groups=[elastic_security_group],
            logging=aes.LoggingOptions(app_log_enabled=True),
        )
        core.Tags.of(elastic_domain).add("project", constants["PROJECT_TAG"])

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
                vpc=vpc_stack.output_props["vpc"],
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True
                ),
                key_name=constants["KEY_PAIR"],
                security_group=elastic_client_security_group,
                user_data=elastic_userdata,
            )
            core.Tags.of(elastic_instance).add("project", constants["PROJECT_TAG"])
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
            elastic_instance.instance.cfn_options.creation_policy = (
                core.CfnCreationPolicy(
                    resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
                )
            )

        self.output_props = {}
        self.output_props["elastic_security_group"] = elastic_security_group

    # properties
    @property
    def outputs(self):
        return self.output_props
