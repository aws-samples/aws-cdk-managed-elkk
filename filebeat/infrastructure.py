# import modules
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
    Aws,
    CfnCreationPolicy,
    CfnResourceSignal,
    Duration,
    Stack,
    Tags,
)

from helpers.functions import (
    file_updated,
    user_data_init,
    instance_add_log_permissions,
)

# set path
from pathlib import Path

dirname = Path(__file__).parent


class FilebeatStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        MSK_BROKERS: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # log generator asset
        log_generator_py = assets.Asset(
            self,
            "log_generator",
            path=str(dirname.joinpath("log_generator.py")),
        )
        # log generator requirements.txt asset
        log_generator_requirements_txt = assets.Asset(
            self,
            "log_generator_requirements_txt",
            path=str(dirname.joinpath("log_generator_requirements.txt")),
        )

        # get kafka brokers
        kafka_brokers = f'''"{MSK_BROKEeS.replace(",", '", "')}"'''

        # update filebeat.yml to .asset
        filebeat_yml_asset = file_updated(
            str(dirname.joinpath("filebeat.yml")),
            {"$kafka_brokers": kafka_brokers},
        )
        filebeat_yml = assets.Asset(self, "filebeat_yml", path=filebeat_yml_asset)
        elastic_repo = assets.Asset(
            self, "elastic_repo", path=str(dirname.joinpath("elastic.repo"))
        )
        # userdata for Filebeat
        fb_userdata = user_data_init(log_group_name="elkk/filebeat/instance")
        # instance for Filebeat
        fb_instance = ec2.Instance(
            self,
            "filebeat_client",
            instance_type=ec2.InstanceType(constants["FILEBEAT_INSTANCE"]),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            # use init over userdata ...
            init=ec2.CloudFormationInit.from_config_sets(
                config_sets={"default": ["awsLogs", "kafka"]},
                configs={
                    "awsLogs": constants["init_awslogs"](stack_name=Aws.STACK_NAME),
                    "filebeat": ec2.InitConfig(
                        [
                            # get setup assets files
                            ec2.InitCommand.shell_command(
                                f"aws s3 cp s3://{filebeat_yml.s3_bucket_name}/{filebeat_yml.s3_object_key} /home/ec2-user/filebeat.yml",
                            ),
                            ec2.InitCommand.shell_command(
                                f"aws s3 cp s3://{log_generator_py.s3_bucket_name}/{log_generator_py.s3_object_key} /home/ec2-user/log_generator.py",
                            ),
                            ec2.InitCommand.shell_command(
                                f"aws s3 cp s3://{log_generator_requirements_txt.s3_bucket_name}/{log_generator_requirements_txt.s3_object_key} /home/ec2-user/requirements.txt",
                            ),
                            # get python3
                            ec2.InitPackage.yum("python3"),
                            # get pip
                            ec2.InitPackage.yum("python-pip"),
                            # make log generator executable
                            ec2.InitCommand.shell_command(
                                "chmod +x /home/ec2-user/log_generator.py"
                            ),
                            # get log generator requirements
                            ec2.InitCommand.shell_command(
                                "python3 -m pip install -r /home/ec2-user/requirements.txt"
                            ),
                            # Filebeat
                            ec2.InitCommand.shell_command(
                                "rpm --import https://packages.elastic.co/GPG-KEY-elasticsearch"
                            ),
                            # move Filebeat repo file
                            ec2.InitCommand.shell_command(
                                "mv -f /home/ec2-user/elastic.repo /etc/yum.repos.d/elastic.repo"
                            ),
                            # install Filebeat
                            ec2.InitCommand.shell_command("yum install filebeat -y"),
                            # move filebeat.yml to final location
                            ec2.InitCommand.shell_command(
                                "mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml"
                            ),
                            # update log generator ownership
                            ec2.InitCommand.shell_command(
                                "chown -R ec2-user:ec2-user /home/ec2-user"
                            ),
                            # start Filebeat
                            ec2.InitCommand.shell_command("systemctl start filebeat"),
                        ]
                    ),
                },
            ),
            init_options={
                "config_sets": ["default"],
                "timeout": Duration.minutes(30),
            },
            vpc=constants["vpc"],
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            key_name=constants["KEY_PAIR"],
            security_group=constants["kafka_client_security_group"],
            user_data=fb_userdata,
        )
        Tags.of(fb_instance).add("project", constants["PROJECT_TAG"])

        # create policies for EC2 to connect to kafka
        access_kafka_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kafka:ListClusters",
                "kafka:GetBootstrapBrokers",
            ],
            resources=["*"],
        )
        # add the role permissions
        fb_instance.add_to_role_policy(statement=access_kafka_policy)
        # add log permissions
        instance_add_log_permissions(fb_instance)
        # add access to the file asset
        filebeat_yml.grant_read(fb_instance)
        elastic_repo.grant_read(fb_instance)
        log_generator_py.grant_read(fb_instance)
        log_generator_requirements_txt.grant_read(fb_instance)
        # add creation policy for instance
        fb_instance.instance.cfn_options.creation_policy = CfnCreationPolicy(
            resource_signal=CfnResourceSignal(count=1, timeout="PT10M")
        )
