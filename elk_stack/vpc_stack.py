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
        self.elk_vpc = ec2.Vpc(self, "elk_vpc", max_azs=3)
        core.Tag.add(self.elk_vpc, "project", ELK_PROJECT_TAG)
    
    def get_vpc(self) -> ec2.Vpc:
        return self.elk_vpc

    def get_subnet_ids_public(self) -> list:
        return self.elk_vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids

