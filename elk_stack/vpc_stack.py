# import modules
import os
from aws_cdk import (
    core,
    aws_ec2 as ec2,
)
from elk_stack.constants import ELK_PROJECT_TAG

dirname = os.path.dirname(__file__)


class VpcStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # create the vpc
        self.elk_vpc = ec2.Vpc(self, "elk_vpc", max_azs=3,)
        core.Tag.add(self.elk_vpc, "project", ELK_PROJECT_TAG)
        # add s3 endpoint
        self.elk_vpc.add_gateway_endpoint(
            "e6ad3311-f566-426e-8291-6937101db6a1",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

    # properties to share with other stacks ...
    @property
    def get_vpc(self):
        return self.elk_vpc

    @property
    def get_vpc_public_subnet_ids(self):
        return self.elk_vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids

    @property
    def get_vpc_private_subnet_ids(self):
        return self.elk_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE
        ).subnet_ids
