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


class KibanaLambdaUpdate(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        lambda_function = lambda_python.PythonFunction(
            self,
            "lambda_function",
            entry=str(dirname),
            handler="lambda_handler",
            index="lambda_function.py",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:ListBucket",
                        "s3:ListAllMyBuckets",
                        "lambda:ListFunctions",
                        "lambda:UpdateFunctionConfiguration",
                        "cloudfront:ListDistributions",
                        "s3:GetBucketTagging",
                        "es:ListDomainNames",
                        "es:DescribeElasticsearchDomain",
                    ],
                    resources=["*"],
                )
            ],
        )

        # cleaner custom provider
        kibana_lambda_update_provider = cr.Provider(
            self,
            "kibana_lambda_update_provider",
            on_event_handler=lambda_function,
        )

        # custom resources
        kibana_lambda_update_resource = core.CustomResource(
            self,
            "kibana_lambda_update_resource",
            service_token=kibana_lambda_update_provider.service_token,
        )
