# import modules
import urllib.request

from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as assets,
)
from helpers.functions import (
    file_updated,
    kafka_get_brokers,
    user_data_init,
    instance_add_log_permissions,
)

# set path
from pathlib import Path

dirname = Path(__file__).parent

external_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")


class FilebeatStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        vpc_stack,
        kafka_stack,
        constants: dict,
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

        # get kakfa brokers
        kafka_brokers = f'''"{kafka_get_brokers().replace(",", '", "')}"'''

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
            vpc=vpc_stack.get_vpc,
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            key_name=constants["KEY_PAIR"],
            security_group=kafka_stack.get_kafka_client_security_group,
            user_data=fb_userdata,
        )
        core.Tag.add(fb_instance, "project", constants["PROJECT_TAG"])

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
        # add commands to the userdata
        fb_userdata.add_commands(
            # get setup assets files
            f"aws s3 cp s3://{filebeat_yml.s3_bucket_name}/{filebeat_yml.s3_object_key} /home/ec2-user/filebeat.yml",
            f"aws s3 cp s3://{elastic_repo.s3_bucket_name}/{elastic_repo.s3_object_key} /home/ec2-user/elastic.repo",
            f"aws s3 cp s3://{log_generator_py.s3_bucket_name}/{log_generator_py.s3_object_key} /home/ec2-user/log_generator.py",
            f"aws s3 cp s3://{log_generator_requirements_txt.s3_bucket_name}/{log_generator_requirements_txt.s3_object_key} /home/ec2-user/requirements.txt",
            # get python3
            "yum install python3 -y",
            # get pip
            "yum install python-pip -y",
            # make log generator executable
            "chmod +x /home/ec2-user/log_generator.py",
            # get log generator requirements
            "python3 -m pip install -r /home/ec2-user/requirements.txt",
            # Filebeat
            "rpm --import https://packages.elastic.co/GPG-KEY-elasticsearch",
            # move Filebeat repo file
            "mv -f /home/ec2-user/elastic.repo /etc/yum.repos.d/elastic.repo",
            # install Filebeat
            "yum install filebeat -y",
            # move filebeat.yml to final location
            "mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml",
            # update log generator ownership
            "chown -R ec2-user:ec2-user /home/ec2-user",
            # start Filebeat
            "systemctl start filebeat",
        )
        # add the signal
        fb_userdata.add_signal_on_exit_command(resource=fb_instance)
        # attach the userdata
        fb_instance.add_user_data(fb_userdata.render())
        # add creation policy for instance
        fb_instance.instance.cfn_options.creation_policy = core.CfnCreationPolicy(
            resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
        )
