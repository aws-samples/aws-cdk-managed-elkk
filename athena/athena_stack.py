# import modules
from aws_cdk import core, aws_s3 as s3, aws_iam as iam, aws_glue as glue

# from helpers.custom_resource import CustomResource
from bucket_cleaner.custom_resource import BucketCleaner

# set path
from pathlib import Path

dirname = Path(__file__).parent

class AthenaStack(core.Stack):
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
        core.Tags.of(s3_bucket).add("project", constants["PROJECT_TAG"])

        # cleaner action on delete
        s3_bucket_cleaner = BucketCleaner(
            self,
            "s3_bucket_cleaner",
            buckets=[s3_bucket],
            lambda_description=f"On delete empty {core.Stack.stack_name} S3 buckets",
        )

        self.output_props = {}
        self.output_props["s3_bucket"] = s3_bucket


    # properties
    @property
    def outputs(self):
        return self.output_props
