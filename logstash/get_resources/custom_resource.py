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


class GetResources(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # update asset lambda
        on_event_lambda = lambda_python.PythonFunction(
            self,
            "on_event_lambda",
            description=f"Get resources",
            entry=str(dirname.joinpath("on_event")),
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

        # asset updater provider
        provider = cr.Provider(
            self,
            "provider",
            on_event_handler=on_event_lambda,
        )

        # custom resource
        resource = core.CustomResource(
            self,
            "resource",
            service_token=provider.service_token,
        )

        self.output_props = {}

    # properties
    @property
    def outputs(self):
        return self.output_props