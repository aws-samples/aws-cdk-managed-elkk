from aws_cdk import (
    aws_cloudformation as cfn,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python as lambda_python,
    aws_logs as logs,
    core,
    custom_resources as cr,
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
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # cleaner lambda
        on_event_lambda = lambda_python.PythonFunction(
            self,
            "on_event_lambda",
            description=f"On delete empty {core.Stack.stack_name} S3 buckets",
            entry=str(dirname.joinpath("on_event")),
            environment={
                "BUCKETS": json.dumps([f"{bucket.bucket_name}" for bucket in buckets]),
            },
            handler="lambda_handler",
            index="lambda_function.py",
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
        is_complete_lambda = lambda_python.PythonFunction(
            self,
            "is_complete_lambda",
            description=f"Confirm empty {core.Stack.stack_name} S3 buckets",
            entry=str(dirname.joinpath("is_complete")),
            environment={
                "BUCKETS": json.dumps([f"{bucket.bucket_name}" for bucket in buckets]),
            },
            handler="lambda_handler",
            index="lambda_function.py",
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
        provider = cr.Provider(
            self,
            "cleaner_provider",
            on_event_handler=on_event_lambda,
            is_complete_handler=is_complete_lambda,
        )

        # custom resources
        resource = core.CustomResource(
            self,
            "bucket_cleaner_resource",
            service_token=provider.service_token,
        )

        # dependencies
        for bucket in buckets:
            resource.node.add_dependency(bucket)