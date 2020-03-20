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
    aws_logs as logs,
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

        # bucket policy for origin
        # https://github.com/aws/aws-cdk/issues/941

        # the lambda behind the api
        kibana_lambda = lambda_.Function(
            self,
            "kibana_lambda",
            description="kibana api gateway lambda",
            code=lambda_.Code.from_asset(os.path.join(dirname, "kibana_lambda.zip")),
            handler="lambda_function.lambda_handler",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
            vpc=vpc_stack.get_vpc,
            security_groups=[elastic_stack.elastic_security_group],
            log_retention=logs.RetentionDays.ONE_WEEK,
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

        # kibana bucket empty policies
        kibana_bucket_empty_policy = [
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
        kibana_bucket_empty = CustomResource(
            self,
            "kibana_bucket_empty",
            PhysicalId="kibanaBucketEmpty",
            Description="Empty kibana cache s3 bucket",
            Uuid="f7d4f730-4ee1-13e8-9c2d-fa7ae06bbebc",
            HandlerPath=os.path.join(dirname, "../helpers/s3_bucket_empty.py"),
            BucketName=kibana_bucket.bucket_name,
            ResourcePolicies=kibana_bucket_empty_policy,
        )
        # tag the lamdbda
        core.Tag.add(kibana_bucket_empty, "project", constants["PROJECT_TAG"])
        # needs a dependancy
        kibana_bucket_empty.node.add_dependency(kibana_bucket)

        # kibana lambda update policies
        kibana_lambda_update_policy = [
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
        ]
        # create the kibana lambda update
        kibana_lambda_update = CustomResource(
            self,
            "kibana_lambda_update",
            Description="Update ENV vars for kibana api lambda",
            PhysicalId="kibanaLambdaUpdate",
            Uuid="f7d4f230-4ee1-07e8-9c2d-fa7ae06bbebc",
            HandlerPath=os.path.join(dirname, "../helpers/lambda_env_update.py"),
            ResourcePolicies=kibana_lambda_update_policy,
        )
        # tag the lamdbda
        core.Tag.add(kibana_lambda_update, "project", constants["PROJECT_TAG"])
        # needs a dependancy
        kibana_lambda_update.node.add_dependency(kibana_bucket)
        kibana_lambda_update.node.add_dependency(kibana_distribution)

        core.CfnOutput(
            self,
            "kibana_link",
            value=f"https://{kibana_distribution.domain_name}/_plugin/kibana",
            description="Kibana Web Url",
            export_name="kibana-link",
        )

