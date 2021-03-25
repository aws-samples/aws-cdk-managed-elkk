# import modules
from aws_cdk import (
    core,
    aws_ec2 as ec2,
)

class VpcStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, constants: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # import the vpc from context
        try:
            vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=constants["VPC_ID"])
        # if no vpc in context then create
        except KeyError:
            vpc = ec2.Vpc(self, "vpc", max_azs=3)
            # tag the vpc
            core.Tags.of(vpc).add("project", constants["PROJECT_TAG"])

            # add s3 endpoint
            vpc.add_gateway_endpoint(
                "e6ad3311-f566-426e-8291-6937101db6a1",
                service=ec2.GatewayVpcEndpointAwsService.S3,
            )

        self.output_props = {}
        self.output_props["vpc"] = vpc

    # properties
    @property
    def outputs(self):
        return self.output_props

