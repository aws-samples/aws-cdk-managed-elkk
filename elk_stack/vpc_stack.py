# import modules
import os
from aws_cdk import (
    core,
    aws_ec2 as ec2,
)
from constants import ELK_PROJECT_TAG

dirname = os.path.dirname(__file__)


class VpcStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # create the vpc
        self.elk_vpc = ec2.Vpc(self, "elk_vpc", max_azs=3,)
        core.Tag.add(self.elk_vpc, "project", ELK_PROJECT_TAG)
        # add s3 endpoint
        self.elk_vpc.add_gateway_endpoint("1234", service=ec2.GatewayVpcEndpointAwsService.S3,)

    # properties
    @property
    def get_vpc(self):
        return self.elk_vpc

