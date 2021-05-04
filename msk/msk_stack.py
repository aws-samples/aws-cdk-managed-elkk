# import modules
from aws_cdk import (
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
    core,
)

from msk.msk_attributes.custom_resource import MskAttributes
from ensure_service_linked_role.custom_resource import EnsureServiceLinkedRole

# set path
from pathlib import Path

dirname = Path(__file__).parent


class MskStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        constants: dict,
        client: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ensure that the service linked role exists
        EnsureServiceLinkedRole(
            self, "ensure_msk_service_role", service="kafka.amazonaws.com"
        )

        # create assets
        client_properties = assets.Asset(
            self, "client_properties", path=str(dirname.joinpath("client.properties"))
        )

        # security group for kafka clients
        kafka_client_security_group = ec2.SecurityGroup(
            self,
            "kafka_client_security_group",
            vpc=constants["vpc"],
            description="kafka client security group",
            allow_all_outbound=True,
        )
        core.Tags.of(kafka_client_security_group).add(
            "project", constants["PROJECT_TAG"]
        )
        core.Tags.of(kafka_client_security_group).add("name", "kafka_client_sg")

        # Open port 22 for SSH
        kafka_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{constants['external_ip']}/32"),
            ec2.Port.tcp(22),
            "from own public ip",
        )

        # security group for msk
        msk_security_group = ec2.SecurityGroup(
            self,
            "msk_security_group",
            vpc=constants["vpc"],
            description="msk security group",
            allow_all_outbound=True,
        )
        core.Tags.of(msk_security_group).add("project", constants["PROJECT_TAG"])
        core.Tags.of(msk_security_group).add("name", "msk_sg")

        # add ingress for kafka security group
        msk_security_group.connections.allow_from(
            msk_security_group,
            ec2.Port.all_traffic(),
            "within msk",
        )
        msk_security_group.connections.allow_from(
            kafka_client_security_group,
            ec2.Port.all_traffic(),
            "from kafka client sg",
        )

        # ingress for kc sg
        kafka_client_security_group.connections.allow_from(
            msk_security_group,
            ec2.Port.all_traffic(),
            "from msk",
        )

        # create the kafka cluster
        msk_cluster = msk.CfnCluster(
            self,
            "msk_cluster",
            broker_node_group_info={
                "clientSubnets": constants["vpc"]
                .select_subnets(subnet_type=ec2.SubnetType.PUBLIC)
                .subnet_ids,
                "instanceType": constants["KAFKA_INSTANCE_TYPE"],
                "numberOfBrokerNodes": constants["KAFKA_BROKER_NODES"],
                "securityGroups": [msk_security_group.security_group_id],
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
        core.Tags.of(msk_cluster).add("project", constants["PROJECT_TAG"])

        # custom resource for additional properties
        msk_attributes = MskAttributes(
            self,
            "msk_attributes",
            msk_cluster=msk_cluster,
        )
        # need to add the dependency before turning into dict
        msk_attributes.node.add_dependency(msk_cluster)
        msk_attributes = msk_attributes.output_props

        init_awslogs = ec2.InitConfig(
            [
                ec2.InitCommand.shell_command(
                    "yum update -y",
                ),
                ec2.InitPackage.yum("awslogs"),
                ec2.InitCommand.shell_command(
                    "sed -i 's#log_group_name = /var/log/messages#log_group_name = elkk/msk/instances#' /etc/awslogs/awslogs.conf"
                ),
                ec2.InitService.enable("awslogsd"),
                ec2.InitCommand.shell_command(
                    f"sudo -u ec2-user aws configure set region {core.Aws.REGION}",
                ),
            ]
        )

        # instance for kafka client and check for the key pair
        if client:

            # create the instance
            kafka_client_instance = ec2.Instance(
                self,
                "kafka_client",
                instance_type=ec2.InstanceType(constants["KAFKA_CLIENT_INSTANCE"]),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
                # use init over userdata ...
                init=ec2.CloudFormationInit.from_config_sets(
                    config_sets={"default": ["awsLogs", "kafka"]},
                    configs={
                        "awsLogs": init_awslogs,
                        "kafka": ec2.InitConfig(
                            [
                                # get setup assets files
                                ec2.InitCommand.shell_command(
                                    f"aws s3 cp s3://{client_properties.s3_bucket_name}/{client_properties.s3_object_key} /home/ec2-user/client.properties"
                                ),
                                # install java
                                ec2.InitPackage.yum("java-1.8.0-openjdk"),
                                # download kafka
                                ec2.InitCommand.shell_command(
                                    f'wget https://www-us.apache.org/dist/kafka/{constants["KAFKA_DOWNLOAD_VERSION"].split("-")[-1]}/{constants["KAFKA_DOWNLOAD_VERSION"]}.tgz'
                                ),
                                # extract kafka
                                ec2.InitCommand.shell_command(
                                    f"tar -xvf {constants['KAFKA_DOWNLOAD_VERSION']}.tgz",
                                ),
                                # get setup assets files
                                ec2.InitCommand.shell_command(
                                    f"aws s3 cp s3://{client_properties.s3_bucket_name}/{client_properties.s3_object_key} /home/ec2-user/client.properties"
                                ),
                                # update java
                                ec2.InitCommand.shell_command(
                                    "yum install java-1.8.0 -y"
                                ),
                                # install kakfa
                                ec2.InitCommand.shell_command(
                                    f'wget https://www-us.apache.org/dist/kafka/{constants["KAFKA_DOWNLOAD_VERSION"].split("-")[-1]}/{constants["KAFKA_DOWNLOAD_VERSION"]}.tgz'
                                ),
                                ec2.InitCommand.shell_command(
                                    f"tar -xvf {constants['KAFKA_DOWNLOAD_VERSION']}.tgz"
                                ),
                                ec2.InitCommand.shell_command(
                                    f"mv {constants['KAFKA_DOWNLOAD_VERSION']} /opt"
                                ),
                                ec2.InitCommand.shell_command(
                                    f"rm {constants['KAFKA_DOWNLOAD_VERSION']}.tgz"
                                ),
                                # move client.properties to correct location
                                ec2.InitCommand.shell_command(
                                    f"mv -f /home/ec2-user/client.properties /opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/client.properties"
                                ),
                            ]
                        ),
                    },
                ),
                init_options={
                    "config_sets": ["default"],
                    "timeout": core.Duration.minutes(30),
                },
                vpc=constants["vpc"],
                vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                key_name=constants["KEY_PAIR"],
                security_group=kafka_client_security_group,
            )
            core.Tags.of(kafka_client_instance).add("project", constants["PROJECT_TAG"])
            # needs kafka cluster to be available
            kafka_client_instance.node.add_dependency(msk_cluster)

            # create policies for EC2 to connect to Kafka
            access_kafka_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kafka:ListClusters",
                    "kafka:GetBootstrapBrokers",
                    "kafka:DescribeCluster",
                ],
                resources=["*"],
            )
            kafka_client_instance.add_to_role_policy(statement=access_kafka_policy)

            # add log permissions
            logs_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=["*"],
            )
            # add policy to instance
            kafka_client_instance.add_to_role_policy(statement=logs_policy)
            # add access to the file asset
            client_properties.grant_read(kafka_client_instance)

            # cfn outputs
            core.CfnOutput(
                self,
                "kafka_client_instance_string",
                value=f"ssh ec2-user@{kafka_client_instance.instance_public_dns_name}",
                export_name="kafka-client-instance-string",
            )
            core.CfnOutput(
                self,
                "msk_make_topic_elkktopic",
                value=f"make_topic=`/opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/kafka-topics.sh --create --zookeeper {msk_attributes['msk_zookeeper']} --replication-factor 3 --partitions 1 --topic elkktopic 2>&1`",
                export_name="msk-make-topic-elkktopic",
            )
            core.CfnOutput(
                self,
                "msk_connect_producer",
                value=f"/opt/kafka_2.13-2.7.0/bin/kafka-console-producer.sh --broker-list {msk_attributes['msk_brokers']} --topic elkktopic",
                export_name="msk-connect-producer",
            )
            core.CfnOutput(
                self,
                "msk_connect_consumer",
                value=f"/opt/kafka_2.13-2.7.0/bin/kafka-console-consumer.sh --bootstrap-server {msk_attributes['msk_brokers']} --topic elkktopic --from-beginning",
                export_name="msk-connect-consumer",
            )

        # props
        self.output_props = {}
        self.output_props["msk_security_group"] = msk_security_group
        self.output_props["kafka_client_security_group"] = kafka_client_security_group
        self.output_props["input_awslogs"] = init_awslogs
        self.output_props["msk_brokers"] = msk_attributes["msk_brokers"]

    # properties
    @property
    def outputs(self):
        return self.output_props
