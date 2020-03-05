# import modules
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_iam as iam,
)
from elk_stack.custom_resource import CustomResource
from elk_stack.constants import ELK_PROJECT_TAG, ELK_TOPIC
import os

# set path
dirname = os.path.dirname(__file__)


class AthenaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # assets for athena

        # create s3 bucket for athena data
        self.s3_bucket = s3.Bucket(
            self,
            "s3_bucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=core.RemovalPolicy.DESTROY,
            lifecycle_rules=[s3.LifecycleRule(
                # delete the files after 1800 days (5 years)
                expiration=core.Duration.days(1800),
                transitions=[
                    # move files into glacier after 90 days
                    s3.Transition(transition_after=core.Duration.days(90), storage_class=s3.StorageClass.GLACIER)
                ],
            )],
        )
        # tag the bucket
        core.Tag.add(self.s3_bucket, "project", ELK_PROJECT_TAG)

        # lambda policies
        s3_cleaner_policies = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW, actions=["s3:ListBucket"], resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:DeleteObject",],
                resources=[f"{self.s3_bucket.bucket_arn}/*"],
            ),
        ]

        # create the custom resource
        s3_cleaner = CustomResource(
            self,
            "s3_cleaner",
            HandlerPath=os.path.join(dirname, "s3_cleaner_handler.py"),
            BucketName=self.s3_bucket.bucket_name,
            ResourcePolicies=s3_cleaner_policies,
        )
        # needs a dependancy
        s3_cleaner.node.add_dependency(self.s3_bucket)

    # properties
    @property
    def get_s3_bucket(self):
        return self.s3_bucket
