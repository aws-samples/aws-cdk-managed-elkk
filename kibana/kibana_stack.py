# import modules
import os
from subprocess import call
from aws_cdk import (
    core,
    aws_lambda as lambda_,
    aws_ecr_assets as ecr_assets,
)
from helpers.constants import constants

dirname = os.path.dirname(__file__)


class KibanaStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, build_zip: bool = True, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # check a hash of the lambda file
        # if hash has changed then rebuild the zip
        if build_zip:
            # build the image
            call(["docker", "build", "--tag", "kibana-lambda", "."], cwd=dirname)
            call(
                ["docker", "create", "-ti", "--name", "dummy", "kibana-lambda", "bash"],
                cwd=dirname,
            )
            call(["docker", "cp", "dummy:kibana_lambda.zip", "."], cwd=dirname)
            call(["docker", "rm", "-f", "dummy"], cwd=dirname)

        # the lambda
        kibana_lambda = lambda_.Function(
            self,
            "Singleton",
            code=lambda_.Code.from_asset(os.path.join(dirname, "kibana_lambda.zip")),
            handler="lambda_handler.main",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
