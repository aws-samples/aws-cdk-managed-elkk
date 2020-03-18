# import modules
import os
from subprocess import call
from aws_cdk import (
    core,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
)

from helpers.constants import constants
from helpers.functions import elastic_get_endpoint, elastic_get_domain

dirname = os.path.dirname(__file__)


class KibanaStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id_: str,
        elastic_stack,
        build_zip: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, id_, **kwargs)

        # rebuild the lambda if changed
        if build_zip:
            call(["docker", "build", "--tag", "kibana-lambda", "."], cwd=dirname)
            call(
                ["docker", "create", "-ti", "--name", "dummy", "kibana-lambda", "bash"],
                cwd=dirname,
            )
            call(["docker", "cp", "dummy:/tmp/kibana_lambda.zip", "."], cwd=dirname)
            call(["docker", "rm", "-f", "dummy"], cwd=dirname)

        kibana_bucket = s3.Bucket(
            self,
            "kibana_bucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # the lambda behind the api
        kibana_lambda = lambda_.Function(
            self,
            "kibana_lambda",
            code=lambda_.Code.from_asset(os.path.join(dirname, "kibana_lambda.zip")),
            handler="lambda_function.lambda_handler",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            environment={
                "AES_DOMAIN_ENDPOINT": elastic_get_endpoint(),
                "KIBANA_BUCKET": kibana_bucket.bucket_name,
                "S3_MAX_AGE": "2629746",
                "LOG_LEVEL": "warning",
            },
        )

        # the api gateway
        kibana_api = apigw.LambdaRestApi(self, "kibana_api", handler=kibana_lambda,)

        kibana_identity = cloudfront.OriginAccessIdentity(self, "kibana_identity")

        kibana_api_domain = "/".join(kibana_api.url.split("/")[1:-2])[1:]
        kibana_api_path = f'/{"/".join(kibana_api.url.split("/")[-2:])}'
        print(kibana_api_path)

        # create the cloudfront distribution
        kibana_distribution = cloudfront.CloudFrontWebDistribution(
            self,
            "kibana_distribution",
            origin_configs=[
                # the lambda source for kibana
                cloudfront.SourceConfiguration(
                    custom_origin_source=cloudfront.CustomOriginConfig(
                        domain_name=kibana_api_domain,
                        origin_protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    origin_path="/prod",
                    behaviors=[cloudfront.Behavior(is_default_behavior=True)],
                ),
                # the s3 bucket source for kibana
                cloudfront.SourceConfiguration(
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=kibana_bucket,
                        origin_access_identity=kibana_identity,
                    ),
                    behaviors=[
                        cloudfront.Behavior(
                            is_default_behavior=False, path_pattern="bucket_cached/*"
                        )
                    ],
                ),
            ],
        )
        # needs api and bucket to be available
        kibana_distribution.node.add_dependency(kibana_api)
        # add to lambda
        # this needs to be manually updated to the correct value ....
        kibana_lambda.add_environment("CLOUNDFRONT_CACHE_URL", "kibana_distribution.domain_name/bucket_cached")