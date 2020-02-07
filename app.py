#!/usr/bin/env python3

# import modules
from aws_cdk import core
from constants import ELK_ACCOUNT, ELK_REGION

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
    vpc_stack.get_vpc,
    client=True,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
kafka_stack.add_dependency(vpc_stack)

# create the elasticsearch domain
elastic_stack = ElasticStack(
    app,
    "elk-elastic",
    vpc_stack.get_vpc,
    kafka_stack,
    client=True,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
elastic_stack.add_dependency(vpc_stack)
# filebeat stack (filebeat on ec2)
filebeat_stack = FilebeatStack(
    app,
    "elk-filebeat",
    vpc_stack.get_vpc,
    kafka_stack.get_kafka_client_security_group,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
filebeat_stack.add_dependency(kafka_stack)

# athena and s3 stack
athena_stack = AthenaStack(
    app,
    "elk-athena",
    vpc_stack.get_vpc,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
# logstash stack
logstash_stack = LogstashStack(
    app,
    "elk-logstash",
    vpc_stack.get_vpc,
    kafka_stack,
    athena_stack.get_s3_bucket,
    env=core.Environment(region=ELK_REGION, account=ELK_ACCOUNT),
)
logstash_stack.add_dependency(kafka_stack)
logstash_stack.add_dependency(elastic_stack)
logstash_stack.add_dependency(athena_stack)
app.synth()
