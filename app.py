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

# Vpc stack
vpc_stack = VpcStack(
    app,
    "elkk-vpc",
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

# Kafka stack
kafka_stack = KafkaStack(
    app,
    "elkk-kafka",
    vpc_stack,
    client=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
kafka_stack.add_dependency(vpc_stack)

# Filebeat stack (Filebeat on EC2)
filebeat_stack = FilebeatStack(
    app,
    "elkk-filebeat",
    vpc_stack,
    kafka_stack,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
filebeat_stack.add_dependency(kafka_stack)

# Elastic stack
elastic_stack = ElasticStack(
    app,
    "elkk-elastic",
    vpc_stack,
    client=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
elastic_stack.add_dependency(vpc_stack)

# Athena stack
athena_stack = AthenaStack(
    app,
    "elkk-athena",
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
athena_stack.add_dependency(vpc_stack)

# Logstash stack
logstash_stack = LogstashStack(
    app,
    "elkk-logstash",
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
