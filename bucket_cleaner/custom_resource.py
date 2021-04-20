from aws_cdk import (
    aws_cloudformation as cfn,
    custom_resources as cr,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python as lambda_python,
    core,
    aws_logs as logs,
)
import json

# set path
from pathlib import Path

dirname = Path(__file__).parent


class BucketCleaner(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        buckets: list,
        lambda_description: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # cleaner lambda
        cleaner_lambda = lambda_python.PythonFunction(
            self,
            "cleaner_lambda",
            description=lambda_description,
            entry=str(dirname),
            environment={
                "BUCKETS": json.dumps([f"{bucket.bucket_name}" for bucket in buckets]),
            },
            handler="lambda_handler",
            index="cleaner_lambda.py",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            initial_policy=[
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
                    resources=[f"{bucket.bucket_arn}/*" for bucket in buckets],
                ),
            ],
        )

        # check empty
        check_lambda = lambda_python.PythonFunction(
            self,
            "check_lambda",
            description=lambda_description,
            entry=str(dirname),
            environment={
                "BUCKETS": json.dumps([f"{bucket.bucket_name}" for bucket in buckets]),
            },
            handler="lambda_handler",
            index="check_lambda.py",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:ListBucket"],
                    resources=["*"],
                ),
            ],
        )

        # cleaner custom provider
        cleaner_cr = cr.Provider(
            self,
            "cleaner",
            on_event_handler=cleaner_lambda,
            is_complete_handler=check_lambda,
        )

        # custom resources
        bucket_cleaner_resource = core.CustomResource(
            self, "bucket_cleaner_resource", service_token=cleaner_cr.service_token
        )

        # dependencies
        for bucket in buckets:
            bucket_cleaner_resource.node.add_dependency(bucket)