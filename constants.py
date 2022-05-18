import os
import urllib.request

from aws_cdk import App, Stack, Environment
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2

# add creator ip
EXTERNAL_IP = urllib.request.urlopen("https://ident.me").read().decode("utf8")

CDK_APP_NAME = "olk"
CDK_APP_PYTHON_VERSION = "3.7"

GITHUB_CONNECTION_ARN = "CONNECTION_ARN"
GITHUB_OWNER = "OWNER"
GITHUB_REPO = "REPO"
GITHUB_TRUNK_BRANCH = "TRUNK_BRANCH"

DEV_ENV = Environment(
    account=os.environ["ELKK_ACCOUNT_DEV"], region=os.environ["ELKK_REGION_DEV"]
)
KEY_PAIR_DEV = "elkk-keypair"

MSK_DOWNLOAD_VERSION_DEV = "kafka_2.13-2.7.0"
MSK_BROKER_NODES_DEV = 3
MSK_KAFKA_VERSION_DEV = "2.3.1"
MSK_INSTANCE_TYPE_DEV = "kafka.m5.large"
MSK_KAFKACLIENT_INSTANCE_TYPE_DEV = ec2.InstanceType.of(
    ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.LARGE
)
MSK_KAFKACLIENT_DOWNLOAD_VERSION_DEV = "kafka_2.13-2.7.0"

# custom resource not working ... 
MSK_BROKERS = "b-2.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:9098,b-3.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:9098,b-1.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:9098"
MSK_ZOOKEEPER ="z-3.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:2181,z-1.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:2181,z-2.olk-dev.5l6i7x.c25.kafka.us-east-1.amazonaws.com:2181" 

PIPELINE_ENV = Environment(account="222222222222", region="eu-west-1")

PROD_ENV = Environment(account="333333333333", region="eu-west-1")
PROD_API_LAMBDA_RESERVED_CONCURRENCY = 10
PROD_DATABASE_DYNAMODB_BILLING_MODE = dynamodb.BillingMode.PROVISIONED

"""
  "context"= {
    "constants": {
      "VPC_ID": "vpc-0d0d2d781734ab8fe",
      "PROJECT_TAG": "elkk",
      "KEY_PAIR": "elk-key-pair",
      "KAFKA_DOWNLOAD_VERSION": "kafka_2.13-2.7.0",
      "KAFKA_BROKER_NODES": 3,
      "KAFKA_VERSION": "2.3.1",
      "KAFKA_INSTANCE_TYPE": "kafka.m5.large",
      "BUILD_KAFKA_CLIENT": true,
      "KAFKA_CLIENT_INSTANCE": "t2.xlarge",
      "FILEBEAT_INSTANCE": "t2.xlarge",
      "ELASTIC_CLIENT_INSTANCE": "t2.xlarge",
      "ELASTIC_MASTER_COUNT": 3,
      "ELASTIC_MASTER_INSTANCE": "r5.large.elasticsearch",
      "ELASTIC_INSTANCE_COUNT": 3,
      "ELASTIC_INSTANCE": "r5.large.elasticsearch",
      "LOGSTASH_INSTANCE": "t2.xlarge"
    }
  }

"""

