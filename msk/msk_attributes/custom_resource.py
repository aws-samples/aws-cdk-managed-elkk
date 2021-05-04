from aws_cdk import (
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python as lambda_python,
    core,
    custom_resources as cr,
)
import json

# set path
from pathlib import Path

dirname = Path(__file__).parent


class MskAttributes(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        msk_cluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)
        
        # get attributes
        on_event_lambda = lambda_python.PythonFunction(
            self,
            "on_event_lambda",
            description=f"Get MSK attributes 1",
            entry=str(dirname.joinpath("on_event")),
            environment={
                "CLUSTER_NAME": msk_cluster.cluster_name,
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
        )

        # cleaner custom provider
        msk_attributes_provider = cr.Provider(
            self,
            "msk_attributes_provider",
            on_event_handler=on_event_lambda,
        )

        # custom resources
        msk_attributes_resource = core.CustomResource(
            self,
            "msk_attributes_resource",
            service_token=msk_attributes_provider.service_token,
        )

        self.output_props = {}
        self.output_props["msk_arn"] = msk_attributes_resource.get_att_string("msk_arn")
        self.output_props["msk_brokers"] = msk_attributes_resource.get_att_string(
            "msk_brokers"
        )
        self.output_props["msk_zookeeper"] = msk_attributes_resource.get_att_string("msk_zookeeper")

    # properties
    @property
    def outputs(self):
        return self.output_props