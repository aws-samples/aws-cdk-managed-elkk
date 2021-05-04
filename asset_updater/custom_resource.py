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


class AssetUpdater(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        asset,
        updates: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # env for lambda
        env = updates
        env["update_bucket"] = asset.s3_bucket_name
        env["update_object"] = asset.s3_object_key

        # update asset lambda
        on_event_lambda = lambda_python.PythonFunction(
            self,
            "on_event_lambda",
            description=f"Update assets",
            entry=str(dirname.joinpath("on_event")),
            environment=env,
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
        asset_updater_provider = cr.Provider(
            self,
            "asset_updater_provider",
            on_event_handler=on_event_lambda,
        )

        # custom resource
        asset_updater_resource = core.CustomResource(
            self,
            "asset_updater_resource",
            service_token=asset_updater_provider.service_token,
        )