import os
from aws_cdk import (
    aws_cloudformation as cfn,
    aws_lambda as lambda_,
    core,
    aws_logs as logs,
)


class CustomResource(core.Construct):
    def __init__(
        self, scope: core.Construct, id: str, Description: str, Uuid: str, **kwargs
    ) -> None:
        super().__init__(scope, id)

        with open(kwargs["HandlerPath"], encoding="utf-8") as fp:
            code_body = fp.read()

        resource = cfn.CustomResource(
            self,
            "Resource",
            provider=cfn.CustomResourceProvider.lambda_(
                lambda_.SingletonFunction(
                    self,
                    "Singleton",
                    description=Description,
                    uuid=Uuid,
                    code=lambda_.InlineCode(code_body),
                    handler="index.main",
                    timeout=core.Duration.seconds(300),
                    runtime=lambda_.Runtime.PYTHON_3_7,
                    initial_policy=kwargs["ResourcePolicies"],
                    log_retention=logs.RetentionDays.ONE_DAY,
                )
            ),
            properties=kwargs,
        )
        # response
        self.response = resource.get_att("Response")

