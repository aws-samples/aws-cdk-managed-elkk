from aws_cdk import (
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


class EnsureServiceLinkedRole(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        service: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # get attributes
        on_event_lambda = lambda_python.PythonFunction(
            self,
            "on_event_lambda",
            description=f"Ensure service linked role for {service}",
            entry=str(dirname.joinpath("on_event")),
            environment={
                "SERVICE": service,
            },
            handler="lambda_handler",
            index="lambda_function.py",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["kafka:ListClusters", "kafka:GetBootstrapBrokers"],
                    resources=["*"],
                ),
            ],
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        # cleaner custom provider
        provider = cr.Provider(
            self,
            "provider",
            on_event_handler=on_event_lambda,
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        # custom resources
        resource = core.CustomResource(
            self,
            "resource",
            service_token=provider.service_token,
        )

        self.output_props = {}
        self.output_props["service_linked_role"] = ""

    # properties
    @property
    def outputs(self):
        return self.output_props