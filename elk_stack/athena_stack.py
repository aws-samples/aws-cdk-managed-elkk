# import modules
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_iam as iam,
)
from elk_stack.custom_resource import CustomResource
from elk_stack.constants import ELK_PROJECT_TAG
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
        )
        # tag the bucket
        core.Tag.add(self.s3_bucket, "project", ELK_PROJECT_TAG)

        # load the sample data file into s3
        # elkstack/2020/02/09/ls.s3.6b510ecb-d9dd-4877-bf3b-32c78b9bccc6.2020-02-09T10.26.part2.txt
        s3_files = s3_deployment.BucketDeployment(
            self,
            "s3_files",
            sources=[s3_deployment.Source.asset(os.path.join(dirname, "s3_files"))],
            destination_bucket=self.s3_bucket,
            destination_key_prefix="elkstack/2020/02/09",
        )

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
        # response from the custom resource
        # print("s3_clenaner.response", s3_cleaner.response)

    # properties
    @property
    def get_s3_bucket(self):
        return self.s3_bucket
