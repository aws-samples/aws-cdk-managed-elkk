import os
from aws_cdk import aws_cloudformation as cfn, aws_lambda as lambda_, core

dirname = os.path.dirname(__file__)


class S3Cleaner(core.Construct):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)

        resource = cfn.CustomResource(
            self,
            "resource",
            provider=cfn.CustomResourceProvider.lambda_(
                lambda_.SingletonFunction(
                    self,
                    "Singleton",
                    uuid="f7d4f730-4ee1-11e8-9c2d-fa7ae01bbebc",
                    code=lambda_.Code.from_asset(
                        os.path.join(dirname, "s3_cleaner")
                    ),
                    handler="s3_cleaner_app.lambda_handler",
                    timeout=core.Duration.seconds(300),
                    runtime=lambda_.Runtime.PYTHON_3_8,
                )
            ),
            properties=kwargs,
        )

        self.response = resource.get_att("Response").to_string()
