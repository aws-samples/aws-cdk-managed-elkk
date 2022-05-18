# import modules
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    Duration,
    RemovalPolicy,
    Tags,
)

# from helpers.custom_resource import CustomResource

# set path
from pathlib import Path

dirname = Path(__file__).parent


class AthenaStack(Stack):
    def __init__(
        self, scope: core.Construct, id: str, constants: dict, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # create s3 bucket for athena data
        s3_bucket = s3.Bucket(
            self,
            "s3_bucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    # delete the files after 1800 days (5 years)
                    expiration=Duration.days(1800),
                    transitions=[
                        # move files into glacier after 90 days
                        s3.Transition(
                            transition_after=Duration.days(90),
                            storage_class=s3.StorageClass.GLACIER,
                        )
                    ],
                )
            ],
        )
        # tag the bucket
        Tags.of(s3_bucket).add("project", constants["PROJECT_TAG"])

        self.s3_bucket = s3_bucket
