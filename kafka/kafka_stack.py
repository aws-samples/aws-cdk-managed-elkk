# import modules
import urllib.request
from aws_cdk import (
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
    core,
)
import boto3

ec2_client = boto3.client("ec2")

# get helpers
from helpers.functions import (
    file_updated,
    kafka_get_brokers,
    ensure_service_linked_role,
    update_kafka_configuration,
    user_data_init,
    instance_add_log_permissions,
)
from kafka.msk_attributes.custom_resource import MskAttributes

# set path
from pathlib import Path

dirname = Path(__file__).parent

external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class KafkaStack(core.Stack):
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
        ensure_service_linked_role("kafka.amazonaws.com")

        # create assets
        client_properties = assets.Asset(
            self, "client_properties", path=str(dirname.joinpath("client.properties"))
        )

        # security group for kafka clients
        kafka_client_security_group = ec2.SecurityGroup(
            self,
            "kafka_client_security_group",
            vpc=vpc_stack.output_props["vpc"],
            description="kafka client security group",
            allow_all_outbound=True,
        )
        core.Tags.of(kafka_client_security_group).add(
            "project", constants["PROJECT_TAG"]
        )
        core.Tags.of(kafka_client_security_group).add("name", "kafka_client_sg")

        # Open port 22 for SSH
        kafka_client_security_group.add_ingress_rule(
            ec2.Peer.ipv4(f"{external_ip}/32"),
            ec2.Port.tcp(22),
            "from own public ip",
        )

        # security group for kafka
        kafka_security_group = ec2.SecurityGroup(
            self,
            "kafka_security_group",
            vpc=vpc_stack.output_props["vpc"],
            description="kafka security group",
            allow_all_outbound=True,
        )
        core.Tags.of(kafka_security_group).add("project", constants["PROJECT_TAG"])
        core.Tags.of(kafka_security_group).add("name", "kafka_sg")

        # add ingress for kafka security group
        kafka_security_group.connections.allow_from(
            kafka_security_group,
            ec2.Port.all_traffic(),
            "within kafka",
        )
        kafka_security_group.connections.allow_from(
            kafka_client_security_group,
            ec2.Port.all_traffic(),
            "from kafka client sg",
        )

        # ingress for kc sg
        kafka_client_security_group.connections.allow_from(
            kafka_security_group,
            ec2.Port.all_traffic(),
            "from kafka",
        )

        # create the kafka cluster
        kafka_cluster = msk.CfnCluster(
            self,
            "kafka_cluster",
            broker_node_group_info={
                "clientSubnets": vpc_stack.output_props["vpc"]
                .select_subnets(subnet_type=ec2.SubnetType.PUBLIC)
                .subnet_ids,
                "instanceType": constants["KAFKA_INSTANCE_TYPE"],
                "numberOfBrokerNodes": constants["KAFKA_BROKER_NODES"],
                "securityGroups": [kafka_security_group.security_group_id],
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
        core.Tags.of(kafka_cluster).add("project", constants["PROJECT_TAG"])

        # custom resource for additional properties
        msk_attributes = MskAttributes(
            self,
            "msk_attributes",
            msk_cluster=kafka_cluster,
        )

        init_awslogs = ec2.InitConfig(
            [
                ec2.InitCommand.shell_command(
                    "yum update -y",
                ),
                ec2.InitPackage.yum("awslogs"),
                ec2.InitCommand.shell_command(
                    "sed -i 's#log_group_name = /var/log/messages#log_group_name = elkk/kafka/instance#' /etc/awslogs/awslogs.conf"
                ),
                ec2.InitService.enable("awslogsd"),
                ec2.InitCommand.shell_command(
                    f"sudo -u ec2-user aws configure set region {core.Aws.REGION}",
                ),
            ]
        )

        # instance for kafka client and check for the key pair
        if constants["BUILD_KAFKA_CLIENT"]:

            if (
                len(
                    ec2_client.describe_key_pairs(
                        KeyNames=[
                            constants["KEY_PAIR"],
                        ],
                    )["KeyPairs"]
                )
                == 1
            ):
                # userdata for kafka client
                kafka_client_userdata = user_data_init(
                    log_group_name="elkk/kafka/instance"
                )
                # create the instance
                kafka_client_instance = ec2.Instance(
                    self,
                    "kafka_client",
                    instance_type=ec2.InstanceType(constants["KAFKA_CLIENT_INSTANCE"]),
                    machine_image=ec2.AmazonLinuxImage(
                        generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                    ),
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
                                ]
                            ),
                        },
                    ),
                    init_options={
                        "config_sets": ["default"],
                        "timeout": core.Duration.minutes(30),
                    },
                    vpc=vpc_stack.output_props["vpc"],
                    vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
                    key_name=constants["KEY_PAIR"],
                    security_group=kafka_client_security_group,
                    # user_data=kafka_client_userdata,
                )
                core.Tags.of(kafka_client_instance).add(
                    "project", constants["PROJECT_TAG"]
                )
                # needs kafka cluster to be available
                kafka_client_instance.node.add_dependency(kafka_cluster)
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
                # add the role permissions
                kafka_client_instance.add_to_role_policy(statement=access_kafka_policy)
                # add log permissions
                instance_add_log_permissions(kafka_client_instance)
                # add access to the file asset
                client_properties.grant_read(kafka_client_instance)
                # update the userdata with commands
                kafka_client_userdata.add_commands(
                    # get setup assets files
                    f"aws s3 cp s3://{client_properties.s3_bucket_name}/{client_properties.s3_object_key} /home/ec2-user/client.properties",
                    # update java
                    "yum install java-1.8.0 -y",
                    # install kakfa
                    f'wget https://www-us.apache.org/dist/kafka/{constants["KAFKA_DOWNLOAD_VERSION"].split("-")[-1]}/{constants["KAFKA_DOWNLOAD_VERSION"]}.tgz',
                    f"tar -xvf {constants['KAFKA_DOWNLOAD_VERSION']}.tgz",
                    f"mv {constants['KAFKA_DOWNLOAD_VERSION']} /opt",
                    f"rm {constants['KAFKA_DOWNLOAD_VERSION']}.tgz",
                    # move client.properties to correct location
                    f"mv -f /home/ec2-user/client.properties /opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/client.properties",
                    # create the topic, if already exists capture error message
                    f"kafka_arn=`aws kafka list-clusters --region {core.Aws.REGION} --output text --query 'ClusterInfoList[*].ClusterArn'`",
                    # get the zookeeper
                    f"kafka_zookeeper=`aws kafka describe-cluster --cluster-arn $kafka_arn --region {core.Aws.REGION} --output text --query 'ClusterInfo.ZookeeperConnectString'`",
                    # create the topics
                    f"make_topic=`/opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic elkktopic 2>&1`",
                    f"make_topic=`/opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic apachelog 2>&1`",
                    f"make_topic=`/opt/{constants['KAFKA_DOWNLOAD_VERSION']}/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic appevent 2>&1`",
                )
                # add the signal
                kafka_client_userdata.add_signal_on_exit_command(
                    resource=kafka_client_instance
                )
                # attach the userdata
                # kafka_client_instance.add_user_data(kafka_client_userdata.render())
            else:
                print(
                    f"Keypair {constants['KEY_PAIR']} not found, instance creation skipped"
                )

        self.output_props = {}
        self.output_props["kafka_client_security_group"] = kafka_client_security_group
        self.output_props["input_awslogs"] = init_awslogs

    # properties
    @property
    def outputs(self):
        return self.output_props
