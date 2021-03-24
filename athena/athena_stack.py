# import modules
from aws_cdk import core, aws_s3 as s3, aws_iam as iam, aws_glue as glue
from helpers.custom_resource import CustomResource
import os

# set path
from pathlib import Path

dirname = Path(__file__).parent

class AthenaStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, constants: dict, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # create s3 bucket for athena data
        self.s3_bucket = s3.Bucket(
            self,
            "s3_bucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=core.RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    # delete the files after 1800 days (5 years)
                    expiration=core.Duration.days(1800),
                    transitions=[
                        # move files into glacier after 90 days
                        s3.Transition(
                            transition_after=core.Duration.days(90),
                            storage_class=s3.StorageClass.GLACIER,
                        )
                    ],
                )
            ],
        )
        # tag the bucket
        core.Tag.add(self.s3_bucket, "project", constants["PROJECT_TAG"])

        # lambda policies
        athena_bucket_empty_policy = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:DeleteObject",
                ],
                resources=[f"{self.s3_bucket.bucket_arn}/*"],
            ),
        ]

        # create the custom resource
        athena_bucket_empty = CustomResource(
            self,
            "athena_bucket_empty",
            PhysicalId="athenaBucketEmpty",
            Description="Empty athena s3 bucket",
            Uuid="f7d4f730-4ee1-11e8-9c2d-fa7ae01bbebc",
            HandlerPath=str(dirname.parent.joinpath("helpers/s3_bucket_empty.py")),
            BucketName=self.s3_bucket.bucket_name,
            ResourcePolicies=athena_bucket_empty_policy,
        )
        # needs a dependancy
        athena_bucket_empty.node.add_dependency(self.s3_bucket)

    # properties
    @property
    def get_s3_bucket(self):
        return self.s3_bucket
