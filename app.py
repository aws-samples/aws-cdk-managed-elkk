##!/usr/bin/env python3
from aws_cdk import App, Stack
from aws_cdk import pipelines

# The AWS CDK application entry point
import constants
from deployment import OLK

app = App()

# Development
OLK(
    app,
    f"{constants.CDK_APP_NAME}-dev",
    env=constants.DEV_ENV,
)

# Production pipeline
# Pipeline(app, f"{constants.CDK_APP_NAME}-pipeline", env=constants.PIPELINE_ENV)

app.synth()

'''
# import modules
import os
from aws_cdk import core

# import cdk classes
from vpc.vpc_stack import VpcStack
# from msk.msk_stack import MskStack
# from filebeat.filebeat_stack import FilebeatStack

from elastic.elastic_stack import ElasticStack
from kibana.kibana_stack import KibanaStack
# from athena.athena_stack import AthenaStack
# from logstash.logstash_stack import LogstashStack

app = core.App()

this_env = core.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

constants = app.node.try_get_context("constants")

# Vpc stack
vpc_stack = VpcStack(app, "elkk-vpc", constants=constants, env=this_env)
constants.update(vpc_stack.output_props)

## Kafka stack
#msk_stack = MskStack(
#    app,
#    "elkk-msk",
##    constants=constants,
#    client=False,
#    env=this_env,
#)
#constants.update(msk_stack.output_props)

# Filebeat stack (Filebeat on EC2)
#filebeat_stack = FilebeatStack(
#    app,
#    "elkk-filebeat",
#    constants=constants,
#    env=this_env,
#)

## Elastic stack
elastic_stack = ElasticStack(
    app,
    "elkk-elastic",
    constants=constants,
    client=False,
    env=this_env,
)
constants.update(elastic_stack.output_props)

# Kibana stack
kibana_stack = KibanaStack(
   app,
   "elkk-kibana",
   constants=constants,
   env=this_env,
)

# Athena stack
# athena_stack = AthenaStack(
#    app,
#    "elkk-athena",
#    constants=constants,
#    env=this_env,
# )
# constants.update(athena_stack.output_props)
#
# Logstash stack
# logstash_stack = LogstashStack(
#    app,
#    "elkk-logstash",
#    constants=constants,
#    logstash_ec2=True,
#    logstash_fargate=False,
#    env=this_env,
# )
print(constants)

# synth the app
app.synth()
'''