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
from kibana.kibana_stack import KibanaStack

app = core.App()

this_env = core.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

constants = app.node.try_get_context("constants")

# Vpc stack
vpc_stack = VpcStack(app, "elkk-vpc", constants=constants, env=this_env)

# Kafka stack
kafka_stack = KafkaStack(
    app,
    "elkk-kafka",
    vpc_stack,
    constants=constants,
    client=True,
    env=this_env,
)
kafka_stack.add_dependency(vpc_stack)

# Filebeat stack (Filebeat on EC2)
filebeat_stack = FilebeatStack(
    app,
    "elkk-filebeat",
    vpc_stack,
    kafka_stack,
    constants=constants,
    env=this_env,
)
filebeat_stack.add_dependency(kafka_stack)

# Elastic stack
elastic_stack = ElasticStack(
    app,
    "elkk-elastic",
    vpc_stack,
    constants=constants,
    client=False,
    env=this_env,
)
elastic_stack.add_dependency(vpc_stack)

# Kibana stack
kibana_stack = KibanaStack(
    app,
    "elkk-kibana",
    vpc_stack,
    elastic_stack,
    constants=constants,
    env=this_env,
)
kibana_stack.add_dependency(elastic_stack)

# Athena stack
athena_stack = AthenaStack(
    app,
    "elkk-athena",
    constants=constants,
    env=this_env,
)
athena_stack.add_dependency(vpc_stack)

# Logstash stack
logstash_stack = LogstashStack(
    app,
    "elkk-logstash",
    vpc_stack,
    constants=constants,
    logstash_ec2=True,
    logstash_fargate=False,
    env=this_env,
)
logstash_stack.add_dependency(kafka_stack)
logstash_stack.add_dependency(elastic_stack)
logstash_stack.add_dependency(athena_stack)

# synth the app
app.synth()
