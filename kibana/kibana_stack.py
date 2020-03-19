# import modules
import os
from subprocess import call
from aws_cdk import (
    core,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_iam as iam,
)
import pathlib

from helpers.constants import constants
from helpers.custom_resource import CustomResource
from helpers.functions import elastic_get_endpoint, elastic_get_domain

dirname = os.path.dirname(__file__)


class KibanaStack(core.Stack):
    def __init__(
        self,
        scope: core.Construct,
        id_: str,
        vpc_stack,
        elastic_stack,
        update_lambda_zip=False,
        **kwargs,
    ) -> None:
        super().__init__(scope, id_, **kwargs)

        # if update lambda zip
        if update_lambda_zip:
            # rebuild the lambda if changed
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
        # tag the bucket
        core.Tag.add(kibana_bucket, "project", constants["PROJECT_TAG"])

        # the lambda behind the api
        kibana_lambda = lambda_.Function(
            self,
            "kibana_lambda",
            description="kibana api gateway lambda",
            code=lambda_.Code.from_asset(os.path.join(dirname, "kibana_lambda.zip")),
            handler="lambda_function.lambda_handler",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            environment={
                "AES_DOMAIN_ENDPOINT": f"https://{elastic_get_endpoint()}",
                "KIBANA_BUCKET": kibana_bucket.bucket_name,
                "S3_MAX_AGE": "2629746",
                "LOG_LEVEL": "warning",
                "CLOUDFRONT_CACHE_URL": "https://kibana_cloudfront_domain_name/bucket_cached",
            },
            vpc=vpc_stack.get_vpc,
            security_groups=[elastic_stack.elastic_security_group],
        )
        # tag the lambda
        core.Tag.add(kibana_lambda, "project", constants["PROJECT_TAG"])
        # create policies for the lambda
        kibana_lambda_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW, actions=["s3:*",], resources=["*"],
        )
        # add the role permissions
        kibana_lambda.add_to_role_policy(statement=kibana_lambda_policy)

        # the api gateway
        kibana_api = apigw.LambdaRestApi(
            self, "kibana_api", handler=kibana_lambda, binary_media_types=["*/*"]
        )
        # tag the api gateway
        core.Tag.add(kibana_api, "project", constants["PROJECT_TAG"])

        kibana_identity = cloudfront.OriginAccessIdentity(self, "kibana_identity")

        kibana_api_domain = "/".join(kibana_api.url.split("/")[1:-2])[1:]
        kibana_api_path = f'/{"/".join(kibana_api.url.split("/")[-2:])}'

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
        # tag the cloudfront distribution
        core.Tag.add(kibana_distribution, "project", constants["PROJECT_TAG"])
        # needs api and bucket to be available
        kibana_distribution.node.add_dependency(kibana_api)

        # lambda policies
        s3_cleaner_policies = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW, actions=["s3:ListBucket"], resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:DeleteObject",],
                resources=[f"{kibana_bucket.bucket_arn}/*"],
            ),
        ]
        # create the custom resource
        s3_cleaner = CustomResource(
            self,
            "s3_cleaner",
            HandlerPath=os.path.join(dirname, "../helpers/s3_cleaner_handler.py"),
            BucketName=kibana_bucket.bucket_name,
            ResourcePolicies=s3_cleaner_policies,
        )
        # tag the lamdbda
        core.Tag.add(s3_cleaner, "project", constants["PROJECT_TAG"])
        # needs a dependancy
        s3_cleaner.node.add_dependency(kibana_bucket)

        # the code from file to inline
        with open(os.path.join(dirname, "lambda_update.py"), encoding="utf-8") as fp:
            code_body = fp.read()

        # the lambda behind the api
        lambda_update = lambda_.SingletonFunction(
            self,
            "lambda_update",
            uuid="f7d4f730-4ee2-31e8-9c2d-fa7ae01bbebc",
            description="update kibana lambda env",
            code=lambda_.InlineCode(code_body),
            handler="index.main",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        # tag the lamdbda
        core.Tag.add(lambda_update, "project", constants["PROJECT_TAG"])
        # needs a dependancy
        lambda_update.node.add_dependency(kibana_distribution)
        lambda_update.node.add_dependency(kibana_bucket)
        # lambda update permissions
        lambda_update.add_to_role_policy(
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
        )
