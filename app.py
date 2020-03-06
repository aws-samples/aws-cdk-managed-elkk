#!/usr/bin/env python3

# import modules
import os
from aws_cdk import core

# import cdk classes
from vpc.vpc_stack import VpcStack
from kafka.kafka_stack import KafkaStack
from elastic.elastic_stack import ElasticStack
from logstash.logstash_stack import LogstashStack
from filebeat.filebeat_stack import FilebeatStack
from athena.athena_stack import AthenaStack

app = core.App()

# create the vpc
vpc_stack = VpcStack(
    app,
    "elk-vpc",
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

# create the kafka cluster
kafka_stack = KafkaStack(
    app,
    "elk-kafka",
    vpc_stack,
    client=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
kafka_stack.add_dependency(vpc_stack)

# filebeat stack (filebeat on ec2)
filebeat_stack = FilebeatStack(
    app,
    "elk-filebeat",
    vpc_stack,
    kafka_stack,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
filebeat_stack.add_dependency(kafka_stack)

# create the elasticsearch domain
elastic_stack = ElasticStack(
    app,
    "elk-elastic",
    vpc_stack,
    client=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
elastic_stack.add_dependency(vpc_stack)

# athena
athena_stack = AthenaStack(
    app, "elk-athena",
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
athena_stack.add_dependency(vpc_stack)

# logstash stack
logstash_stack = LogstashStack(
    app,
    "elk-logstash",
    vpc_stack,
    logstash_ec2=False,
    logstash_fargate=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
logstash_stack.add_dependency(kafka_stack)
logstash_stack.add_dependency(elastic_stack)
logstash_stack.add_dependency(athena_stack)
app.synth()
