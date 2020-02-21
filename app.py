#!/usr/bin/env python3

# import modules
from aws_cdk import core
from elk_stack.constants import ELK_ACCOUNT, ELK_REGION

# import cdk classes
from elk_stack.vpc_stack import VpcStack
from elk_stack.kafka_stack import KafkaStack
from elk_stack.elastic_stack import ElasticStack
from elk_stack.logstash_stack import LogstashStack
from elk_stack.filebeat_stack import FilebeatStack
from elk_stack.athena_stack import AthenaStack

app = core.App()

# create the vpc
vpc_stack = VpcStack(
    app, "elk-vpc", env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)

# create the kafka cluster
kafka_stack = KafkaStack(
    app,
    "elk-kafka",
    vpc_stack,
    client=True,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
kafka_stack.add_dependency(vpc_stack)

# filebeat stack (filebeat on ec2)
filebeat_stack = FilebeatStack(
    app,
    "elk-filebeat",
    vpc_stack,
    kafka_stack,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
filebeat_stack.add_dependency(kafka_stack)

# create the elasticsearch domain
elastic_stack = ElasticStack(
    app,
    "elk-elastic",
    vpc_stack,
    client=True,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
elastic_stack.add_dependency(vpc_stack)

# athena 
athena_stack = AthenaStack(
    app,
    "elk-athena",
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
athena_stack.add_dependency(vpc_stack)

# logstash stack
logstash_stack = LogstashStack(
    app,
    "elk-logstash",
    vpc_stack,
    fargate=True,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
logstash_stack.add_dependency(kafka_stack)
logstash_stack.add_dependency(elastic_stack)
logstash_stack.add_dependency(athena_stack)
app.synth()
