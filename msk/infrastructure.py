# import modules
from constructs import Construct
from aws_cdk import (
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3_assets as assets,
    Aws,
    CfnOutput,
    CustomResource,
    custom_resources as cr,
    Duration,
    Stack,
    Tags,
)
from typing import Any
from pathlib import Path

dirname = Path(__file__).parent


class MskAttributes(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        msk_cluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # get attributes
        on_event_lambda = _lambda.DockerImageFunction(
            self,
            "on_event_lambda",
            code=_lambda.DockerImageCode.from_image_asset(
                str(dirname.joinpath("runtime/mskattributes"))
            ),
            description="Get MSK attributes",
            environment={
                "CLUSTER_NAME": msk_cluster.cluster_name,
            },
            log_retention=logs.RetentionDays.ONE_DAY,
            timeout=Duration.seconds(30),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["kafka:ListClusters", "kafka:GetBootstrapBrokers"],
                    resources=["*"],
                ),
            ],
        )

        msk_attributes_provider = cr.Provider(
            self,
            "msk_attributes_provider",
            on_event_handler=on_event_lambda,
            log_retention=logs.RetentionDays.ONE_DAY
        )

        # custom resources
        msk_attributes_resource = CustomResource(
            self,
            "msk_attributes_resource",
            service_token=msk_attributes_provider.service_token,
        )

        #self.msk_arn = msk_attributes_resource.get_att_string("msk_arn")
        # self.msk_brokers = msk_attributes_resource.get_att_string("msk_brokers")
        # self.msk_zookeeper = msk_attributes_resource.get_att_string("msk_zookeeper")


class MskCluster(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        PROJECT_TAG: str,
        VPC: ec2.Vpc,
        EXTERNAL_IP: str,
        MSK_INSTANCE_TYPE: str,
        MSK_BROKER_NODES: int,
        MSK_KAFKA_VERSION: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # security group for kafka clients
        kafka_client_security_group = ec2.SecurityGroup(
            self,
            "kafka_client_security_group",
            vpc=VPC,
            description="kafka client security group",
            allow_all_outbound=True,
        )
        Tags.of(kafka_client_security_group).add("name", "kafka_client_sg")

        # Open port 22 for SSH
        kafka_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{EXTERNAL_IP}/32"),
            ec2.Port.tcp(22),
            "from own public ip",
        )

        # security group for msk
        msk_security_group = ec2.SecurityGroup(
            self,
            "msk_security_group",
            vpc=VPC,
            description="msk security group",
            allow_all_outbound=True,
        )
        Tags.of(msk_security_group).add("name", "msk_sg")

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
        # configuration info
        msk_configuration = msk.CfnConfiguration(
            self,
            "msk_configuration",
            description="Cluster for ELKK",
            name="ElkkClusterConfig",
            server_properties="auto.create.topics.enable=true",
        )

        # create the kafka cluster
        msk_cluster = msk.CfnCluster(
            self,
            "msk_cluster",
            broker_node_group_info=msk.CfnCluster.BrokerNodeGroupInfoProperty(
                client_subnets=VPC.select_subnets(
                    subnet_type=ec2.SubnetType.PUBLIC
                ).subnet_ids,
                instance_type=MSK_INSTANCE_TYPE,
                security_groups=[msk_security_group.security_group_id],
            ),
            cluster_name=PROJECT_TAG,
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=msk_configuration.ref, revision=1
            ),
            kafka_version=MSK_KAFKA_VERSION,
            number_of_broker_nodes=MSK_BROKER_NODES,
            client_authentication=msk.CfnCluster.ClientAuthenticationProperty(
                sasl=msk.CfnCluster.SaslProperty(
                    iam=msk.CfnCluster.IamProperty(enabled=True),
                )
            ),
            encryption_info=msk.CfnCluster.EncryptionInfoProperty(
                encryption_in_transit=msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker="TLS", in_cluster=True
                )
            ),
            enhanced_monitoring="DEFAULT",
        )

        ## custom resource for additional properties
        msk_attributes = MskAttributes(
          self,
           "msk_attributes",
           msk_cluster=msk_cluster,
        )
        # need to add the dependency before turning into dict
        msk_attributes.node.add_dependency(msk_cluster)

        self.MSK_SECURITY_GROUP = msk_security_group
        self.MSK_KAFKACLIENT_SECURITY_GROUP = kafka_client_security_group
        # self.MSK_BROKERS = msk_attributes.msk_brokers
        # self.MSK_ZOOKEEPER = msk_attributes.msk_zookeeper

        # cfn outputs
        # CfnOutput(
        #     self,
        #     "msk_brokerstring",
        #     value=msk_attributes.msk_brokers,
        #     export_name="mskbrokerstring",
        # )


class KafkaClient(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        KEY_PAIR: str,
        VPC: ec2.Vpc,
        MSK_KAFKACLIENT_INSTANCE_TYPE: ec2.InstanceType,
        MSK_KAFKACLIENT_DOWNLOAD_VERSION: str,
        MSK_KAFKACLIENT_SECURITY_GROUP: ec2.SecurityGroup,
        MSK_BROKERS: str,
        MSK_ZOOKEEPER: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # create assets
        client_properties = assets.Asset(
            self,
            "client_properties",
            path=str(dirname.joinpath("runtime/client.properties")),
        )

        def initAwsLogs(stack_name: str = None):
            # create init_awslogs with current stack name for logs
            init_awslogs = ec2.InitConfig(
                [
                    ec2.InitCommand.shell_command(
                        "yum update -y",
                    ),
                    ec2.InitPackage.yum("awslogs"),
                    ec2.InitCommand.shell_command(
                        f"sed -i 's#log_group_name = /var/log/messages#log_group_name = elkk/{stack_name}/instances#' /etc/awslogs/awslogs.conf"
                    ),
                    ec2.InitService.enable("awslogsd"),
                    ec2.InitCommand.shell_command(
                        f"sudo -u ec2-user aws configure set region {Aws.REGION}",
                    ),
                ]
            )
            return init_awslogs

        # create the instance
        kafka_client_instance = ec2.Instance(
            self,
            "kafka_client",
            instance_type=MSK_KAFKACLIENT_INSTANCE_TYPE,
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            # use init over userdata ...
            init=ec2.CloudFormationInit.from_config_sets(
                config_sets={"default": ["awsLogs", "kafka"]},
                configs={
                    "awsLogs": initAwsLogs(stack_name=Aws.STACK_NAME),
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
                                f'wget https://www-us.apache.org/dist/kafka/{MSK_KAFKACLIENT_DOWNLOAD_VERSION.split("-")[-1]}/{MSK_KAFKACLIENT_DOWNLOAD_VERSION}.tgz'
                            ),
                            # extract kafka
                            ec2.InitCommand.shell_command(
                                f"tar -xvf {MSK_KAFKACLIENT_DOWNLOAD_VERSION}.tgz",
                            ),
                            # get setup assets files
                            ec2.InitCommand.shell_command(
                                f"aws s3 cp s3://{client_properties.s3_bucket_name}/{client_properties.s3_object_key} /home/ec2-user/client.properties"
                            ),
                            # update java
                            ec2.InitCommand.shell_command("yum install java-1.8.0 -y"),
                            # install kakfa
                            ec2.InitCommand.shell_command(
                                f'wget https://www-us.apache.org/dist/kafka/{MSK_KAFKACLIENT_DOWNLOAD_VERSION.split("-")[-1]}/{MSK_KAFKACLIENT_DOWNLOAD_VERSION}.tgz'
                            ),
                            ec2.InitCommand.shell_command(
                                f"tar -xvf {MSK_KAFKACLIENT_DOWNLOAD_VERSION}.tgz"
                            ),
                            ec2.InitCommand.shell_command(
                                f"mv {MSK_KAFKACLIENT_DOWNLOAD_VERSION} /opt"
                            ),
                            ec2.InitCommand.shell_command(
                                f"rm {MSK_KAFKACLIENT_DOWNLOAD_VERSION}.tgz"
                            ),
                            # move client.properties to correct location
                            ec2.InitCommand.shell_command(
                                f"mv -f /home/ec2-user/client.properties /opt/{MSK_KAFKACLIENT_DOWNLOAD_VERSION}/bin/client.properties"
                            ),
                        ]
                    ),
                },
            ),
            init_options={
                "config_sets": ["default"],
                "timeout": Duration.minutes(30),
            },
            vpc=VPC,
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            key_name=KEY_PAIR,
            security_group=MSK_KAFKACLIENT_SECURITY_GROUP,
        )

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
        CfnOutput(
            self,
            "kafka_client_instance_string",
            value=f"ssh ec2-user@{kafka_client_instance.instance_public_dns_name}",
            export_name="kafka-client-instance-string",
        )
        CfnOutput(
            self,
            "msk_make_topic_elkktopic",
            value=f"make_topic=`/opt/{MSK_KAFKACLIENT_DOWNLOAD_VERSION}/bin/kafka-topics.sh --create --zookeeper {MSK_ZOOKEEPER} --replication-factor 3 --partitions 1 --topic elkktopic 2>&1`",
            export_name="msk-make-topic-elkktopic",
        )
        CfnOutput(
            self,
            "msk_connect_producer",
            value=f"/opt/kafka_2.13-2.7.0/bin/kafka-console-producer.sh --broker-list {MSK_BROKERS} --topic elkktopic",
            export_name="msk-connect-producer",
        )
        CfnOutput(
            self,
            "msk_connect_consumer",
            value=f"/opt/kafka_2.13-2.7.0/bin/kafka-console-consumer.sh --bootstrap-server {MSK_BROKERS} --topic elkktopic --from-beginning",
            export_name="msk-connect-consumer",
        )

        self.init_awslogs = initAwsLogs
