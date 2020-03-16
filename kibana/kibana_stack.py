# import modules
import os
from subprocess import call
from aws_cdk import (
    core,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3
)
from aws_cdk.aws_cloudfront import (
    CloudFrontWebDistribution,
    SourceConfiguration,
    CustomOriginConfig,
    OriginProtocolPolicy,
    S3OriginConfig,
    IOriginAccessIdentity
)

from helpers.constants import constants

dirname = os.path.dirname(__file__)


class KibanaStack(core.Stack):
    def __init__(self, scope: core.Construct,
                 id_: str, build_zip: bool = True, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        if build_zip:
            call(
                ['docker', 'build', '--tag', 'kibana-lambda', '.'], 
                cwd=dirname
            )
            call(
                [
                    'docker', 'create', '-ti',
                    '--name', 'dummy', 'kibana-lambda', 'bash'
                ],
                cwd=dirname,
            )
            call(
                ['docker', 'cp', 'dummy:/tmp/kibana_lambda.zip', '.'],
                cwd=dirname
            )
            call(['docker', 'rm', '-f', 'dummy'], cwd=dirname)
        kibana_lambda = lambda_.Function(
            self,
            'Singleton',
            code=lambda_.Code.from_asset(
                os.path.join(dirname, 'kibana_lambda.zip')
            ),
            handler='lambda_function.lambda_handler',
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_8,
        )

        api = apigw.LambdaRestApi(
            self, 'Endpoint',
            handler=kibana_lambda,
        )

        s3_bucket = s3.Bucket(
            self,
            'kibana_bucket',
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        bucket_identity = IOriginAccessIdentity(
            origin_access_identity_name='kibanaBucketIdentity'
        )

        bucket_source = {
            's3_origin_source': S3OriginConfig(
                s3_bucket_source=s3_bucket,
                origin_access_identity=bucket_identity
            ),
            'behaviors': [{'is_default_behavior': False}]
        }
        lambda_source = {
            'custom_origin_source': CustomOriginConfig(
                domain_name=api.domain_name,
                origin_protocol_policy=OriginProtocolPolicy.HTTPS_ONLY
            ),
            'behaviors': [{'is_default_behavior': True}]
        }
        CloudFrontWebDistribution(
            self,
            'KibanaDistribution',
            origin_configs=[
                SourceConfiguration(**bucket_source),
                SourceConfiguration(**lambda_source)
            ]
        )
