# Amazon Managed ELKK
 
This repository contains an implementation example of a managed ELKK stack using the AWS Cloud Development Kit. This example uses Python.

## Table of Contents
1. [Context](#context)
2. [Prerequisites](#prerequisites)
3. [Amazon Virtual Private Cloud](#vpc)
4. [Amazon Managed Streaming for Apache Kafka](#kafka)
5. [Filebeat](#filebeat)
6. [Amazon Elasticsearch Service](#elastic)
7. [Kibana](#kibana)
8. [Amazon Athena](#athena)
9. [Logstash](#logstash)
10. [Clean up](#cleanup)

## Context <a name="context"></a>

The ELKK stack is a pipeline of services to support real-time reporting and analytics. Amazon services can provide a managed ELKK stack using the services Amazon Elasticsearch Service, Logstash on Amazon EC2 or on Amazon Elastic Container Services and Amazon Managed Streaming for Kafka. Kibana is included as a capability of the Amazon Elasticsearch Service. As part of a holistic solution Logstash in addition to outputting logs to Amazon Elasticsearch outputs the log to Amazon S3 for longer term storage. Amazon Athena can be used to directly query files in Amazon S3.

### Components

Filebeat agents will be used to collect the logs from the application/host systems, and publish the logs to Amazon MSK. Filebeat agents are deployed on an Amazon EC2 instance to simulate log generation.

Amazon Managed Streaming for Kafka (Amazon MSK) is used as a buffering layer to handle the collection of logs and manage the back-pressure from downstream components in the architecture. The buffering layer will provide recoverability and extensibility in the platform.

The Logstash layer will perform a dual-purpose of reading the data from Amazon MSK and indexing the logs to Amazon Elasticsearch in real-time as well as storing the data to S3.

Users can search for logs in Amazon Elasticsearch Service using Kibana front-end UI application. Amazon Elasticsearch is a fully managed service which provides a rich set of features such as Dashboards, Alerts, SQL query support and much more which can be used based on workload specific requirements.

Logs are stored in Amazon S3 to support cold data log analysis requirements. AWS Glue catalog will store the metadata information associated with the log files to be made available to the user for ad-hoc analysis.

Amazon Athena supports SQL queries against log data stored in Amazon S3.

![ELKK Architecture](/img/elkk_architecture.png)

-----
## Prerequisites <a name="prerequisites"></a>

The following tools are required to deploy this Amazon Managed ELKK stack.

If using AWS Cloud9 skip to section "AWS Cloud9 - Create Cloud9 Environment" below.

AWS CDK - https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html  
AWS CLI - https://aws.amazon.com/cli/  
Git -  https://git-scm.com/downloads  
python (3.6 or later) - https://www.python.org/downloads/  
Docker - https://www.docker.com/  

Ensure that the kafka version is available via wget. 

### Create the Managed ELKK 

Complete the following steps to set up the Managed ELKK workshop in your environment.

### Set up the environment

```bash
# clone the repo
git clone https://github.com/aws-samples/aws-cdk-managed-elkk
# move to directory
cd aws-cdk-managed-elkk
# bootstrap the remaining setup (assumes us-east-1)
bash bootstrap.sh
# create the virtual environment
python -m venv .env
# activate the virtual environment
source .env/bin/activate
# install the requirements
.env/bin/python -m pip install -r requirements.txt
# create the key pair (if not using an existing key)
# Ensure the the named keypair exists and is accessible.
# The ssh comments using the keypair assume it has been added to the keychain.
aws ec2 create-key-pair --key-name elkk-keypair --query 'KeyMaterial' --output text > elkk-keypair.pem --region us-east-1 --profile elkk
# update key_pair permissions
chmod 400 elkk-keypair.pem
# move key_pair to .ssh
mv -f elkk-keypair.pem $HOME/.ssh/elkk-keypair.pem
# start the ssh agent
eval `ssh-agent -s`
# add your key to keychain
ssh-add -k ~/.ssh/elkk-keypair.pem 
# set the env vars for the dev account
export ELKK_ACCOUNT_DEV="1234567890"
export ELKK_REGION_DEV="us-east-1"
```

### Bootstrap the CDK

Create the CDK configuration by bootstrapping the CDK.

```bash
# bootstrap the cdk
cdk bootstrap aws://${ELKK_ACCOUNT_DEV}/${ELKK_REGION_DEV} --profile elkk
```

![Terminal - Bootstrap the CDK](/img/create_elkk_idx_6.png)

![Terminal - Bootstrap the CDK](/img/create_elkk_idx_7.png)

## Amazon Virtual Private Cloud

Use the AWS CDK to deploy an Amazon VPC across multiple availability zones.

```bash
# deploy the vpc stack
cdk deploy olk-dev/vpcstack --profile elkk
```

![ELKK VPC - 1](/img/elkk_vpc_idx_1.png)

![ELKK VPC - 2](/img/elkk_vpc_idx_2.png)

## Amazon Managed Streaming for Apache Kafka

The second stage in the ELKK deployment is to create the Amazon Managed Streaming for Apache Kafka cluster.
An Amazon EC2 instance is created with the Apache Kafka client installed to interact with the Amazon MSK cluster.

```bash
# deploy the msk cluster
cdk deploy olk-dev/kafka/mskcluster --profile elkk
# deploy the kafka client on an ec2 instance
cdk deploy olk-dev/kafka/kafkaclient --profile elkk
```

When Client is set to True an Amazon EC2 instance is deployed to interact with the Amazon MSK Cluster. It can take up to 30 minutes for the Amazon MSK cluster and client EC2 instance to be deployed.

![ELKK MSK - 2](/img/elkk_kafka_idx_2.png)

Wait until 2/2 checks are completed on the Kafka client EC2 instance to ensure that the userdata scripts have fully run.

![ELKK MSK - 3](/img/elkk_kafka_idx_3.png)

On creation the Kafka client EC2 instance will create three Kafka topics: "elkktopic", "apachelog", and "appevent".

Open a terminal window to connect to connect to the Kafka client Amazon EC2 instance
```bash
# Use stack output elkk-msk.kafkaclientinstancestring to connect to kafka client ec2
# command is similar to the example below
ssh ec2-user@ec2-1-23-45-67.compute-1.amazonaws.com
```

![ElKK MSK - 4](/img/elkk_kafka_idx_4.png)

While connected to the Kafka client EC2 instance create the elkktopic Kafka topic and connect as a producer to the elkktopic topic:
```bash
# Use stack output elkk-msk.mskmaketopicelkktopic to create elkk-topic
# command is similar to the example below
make_topic=`/opt/kafka_2.13-2.7.0/bin/kafka-topics.sh --create --zookeeper z-1.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:2181,z-3.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:2181,z-2.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:2181 --replication-factor 3 --partitions 1 --topic elkktopic 2>&1`
# Use stack output elkk-msk.mskconnectproducer to connect to msk as a producer
# command is similar to the example below
/opt/kafka_2.13-2.7.0/bin/kafka-console-producer.sh --broker-list b-1.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092,b-3.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092,b-2.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092 --topic elkktopic
# create additional opics for "apachelog" and "appevent" using the elkk-msk.msktopicelkktopic command whilst updating the topic name 
```

![ElKK MSK - 5](/img/elkk_kafka_idx_5.png)

Leave the Kafka producer session window open.  

Open a new terminal window and connect to the Kafka client EC2 instance to create a Kafka consumer session:  
```bash
# Use stack output elkk-msk.kafkaclientinstancestring to connect to kafka client ec2
# command is similar to the example below
ssh ec2-user@ec2-1-23-45-67.compute-1.amazonaws.com

![ElKK MSK - 6](/img/elkk_kafka_idx_6.png)

While connected to the Kafka client EC2 instance connect as a consumer to the elkktopic topic:
```bash
# Use stack output elkk-msk.mskconnectproducer to connect to msk as a producer
# command is similar to the example below
/opt/kafka_2.13-2.7.0/bin/kafka-console-consumer.sh --bootstrap-server b-1.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092,b-3.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092,b-2.elkk-stack.fmtxnc.c12.kafka.us-east-1.amazonaws.com:9092 --topic elkktopic --from-beginning
```

![ElKK MSK - 7](/img/elkk_kafka_idx_7.png)

Type messages into the Kafka producer session and they are published to the Amazon MSK cluster

![ElKK MSK - 8](/img/elkk_kafka_idx_8.png)

The messages published to the Amazon MS cluster by the producer session will appear in the Kafka consumer window as they are read from the cluster.

![ElKK MSK - 9](/img/elkk_kafka_idx_9.png)

-----
## Filebeat <a name=filebeat></a>

To simulate incoming logs for the ELKK cluster Filebeat will be installed on an Amazon EC2 instance. Filebeat will harvest logs generated by a dummy log generator and push these logs to the Amazon MSK cluster.

Use the AWS CDK to create an Amazon EC2 instance installed with Filebeat and a dummy log generator.

```bash
# deploy the Filebeat stack
cdk deploy elkk-filebeat
```

![ElKK Filebeat - 1](/img/elkk_filebeat_idx_1.png)

An Amazon EC2 instance is deployed with Filebeat installed and configured to output to Kafka.  

![ElKK Filebeat - 2](/img/elkk_filebeat_idx_2.png)

Wait until 2/2 checks are completed on the Filebeat EC2 instance to ensure that the userdata script has run.

Open a new terminal window connect to the Filebeat EC2 instance and create create dummy logs:

```bash
# get the Filebeat ec2 instance public dns
filebeat_dns=`aws ec2 describe-instances --filter file://filebeat/filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat ec2 instance
ssh ec2-user@$filebeat_dns
```

![ElKK Filebeat - 3](/img/elkk_filebeat_idx_3.png)

While connected to the Filebeat EC2 instance create dummy logs:

```bash
# generate dummy apache logs with log generator
./log_generator.py
```

![ElKK Filebeat - 4](/img/elkk_filebeat_idx_4.png)

Dummy logs created by the log generator will be written to the apachelog folder. Filebeat will harvest the logs and publish them to the Amazon MSK cluster.

In the Kafka client EC2 instance terminal window disconnect the consumer session with <control+c>.

Create Kafka consumer session on the apachelog Kafka topic.

```bash
# Get the cluster ARN
kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a consumer
/opt/kafka_2.13-2.7.0/bin/kafka-console-consumer.sh --bootstrap-server $kafka_brokers --topic apachelog --from-beginning
```

![ElKK Filebeat - 5](/img/elkk_filebeat_idx_5.png)

Messages generated by the log generator should appear in the Kafka consumer terminal window.

![ElKK Filebeat - 6](/img/elkk_filebeat_idx_6.png)

-----
## Amazon Elasticsearch Service <a name=elastic></a>

The Amazon Elasticsearch Service provides an Elasticsearch domain and Kibana dashboards. The elkk-elastic stack also creates an Amazon EC2 instance to interact with the Elasticsearch domain. The EC2 instance can also be used to create an SSH tunnel into the VPC for Kibana dashboard viewing.

```bash
# deploy the elastic stack
cdk deploy elkk-elastic
```

When prompted input "y" for Yes to continue.

![ElKK Elastic - 1](/img/elkk_elastic_idx_1.png)

An Amazon EC2 instance is deployed to interact with the Amazon Elasticsearch Service domain.

New Amazon Elasticsearch Service domains take about ten minutes to initialize.

![ElKK Elastic - 2](/img/elkk_elastic_idx_2.png)

Wait until 2/2 checks are completed on the Amazon EC2 instance to ensure that the userdata script has run.

![ElKK Elastic - 3](/img/elkk_elastic_idx_3.png)

Connect to the EC2 instance using a terminal window:

```bash
# get the elastic ec2 instance public dns
elastic_dns=`aws ec2 describe-instances --filter file://elastic/elastic_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $elastic_dns
# use the public dns to connect to the elastic ec2 instance
ssh ec2-user@$elastic_dns
```

![ElKK Elastic - 4](/img/elkk_elastic_idx_4.png)

While connected to the Elastic EC2 instance:

```bash
# get the elastic domain
elastic_domain=`aws es list-domain-names --output text --query '*'` && echo $elastic_domain
# get the elastic endpoint
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --output text --query 'DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# curl a doc into elasticsearch
curl -XPOST $elastic_endpoint/elkktopic/_doc/ -d '{"message": "Hello - this is a test message"}' -H 'Content-Type: application/json'
# curl to query elasticsearch
curl -XPOST $elastic_endpoint/elkktopic/_search -d' { "query": { "match_all": {} } }' -H 'Content-Type: application/json'
# count the records in the index
curl -GET $elastic_endpoint/elkktopic/_count
# exit the Elastic ec2 instance
exit
```

![ElKK Elastic - 5](/img/elkk_elastic_idx_5.png)

-----
## Kibana <a name=kibana></a>

Amazon Elasticsearch Service has been deployed within a VPC in a private subnet. To allow connections to the Kibana dashboard we deploy a public endpoint using Amazon API Gateway, AWS Lambda, Amazon CloudFront, and Amazon S3.

```bash
# deploy the kibana endpoint
cdk deploy elkk-kibana
```

![Kibana - 1](/img/elkk_kibana_idx_1.png)

When prompted "Do you wish to deploy these changes?", enter "y" for Yes.

![Kibana - 2](/img/elkk_kibana_idx_2.png)

When the deployment is complete the Kibana url is output by the AWS CDK as "elkk-kibana.kibanalink. Click on the link to navigate to Kibana.

![Kibana - 3](/img/elkk_kibana_idx_3.png)

Open the link.

![Kibana - 4](/img/elkk_kibana_idx_4.png)

The Kibana Dashboard is visible.

![Kibana - 5](/img/elkk_kibana_idx_5.png)

To view the records on the Kibana dashboard an "index pattern" needs to be created.

Select "Management" on the left of the Kibana Dashboard.

![Kibana - 6](/img/elkk_kibana_idx_6.png)

Select "Index Patterns" at the top left of the Management Screen.

![Select Index Patterns](/img/elkk_kibana_idx_7.png)

Input an Index Patterns into the Index Pattern field as "elkktopc*".

![Input Pattern](/img/elkk_kibana_idx_8.png)

Click "Next Step".

Click "Create Index Pattern".

The fields from the index can be seen. Click on "Discover".

![Select Discover](/img/elkk_kibana_idx_9.png)

The data can be seen on the Discovery Dashboard.

![Dashboard](/img/elkk_kibana_idx_10.png)

-----
## Amazon Athena <a name=athena></a>

Amazon Simple Storage Service is used to storage logs for longer term storage. Amazon Athena can be used to query files on S3. 

```bash
# deploy the athena stack
cdk deploy elkk-athena
```

![ELKK Athena](/img/elkk_athena_idx_1.png)

![ELKK Athena](/img/elkk_athena_idx_2.png)

-----
## Logstash <a name=logstash></a>

Logstash is deployed to subscribe to the Kafka topics and output the data into Elasticsearch. An additional output is added to push the data into S3. Logstash additionally parses the apache common log format and transforms the log data into json format.

The Logstash pipeline configuration can be viewed in [logstash/logstash.conf](/logstash/logstash.conf)

Check the [/app.py](/app.py) file and verify that the elkk-logstash stack is initially set to deploy Logstash on an Amazon EC2 instance and Amazon Fargate deployment is disabled.

```python
# logstash stack
logstash_stack = LogstashStack(
    app,
    "elkk-logstash",
    vpc_stack,
    logstash_ec2=True,
    logstash_fargate=False,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_ACCOUNT"],
    ),
)
```

When we deploy the elkk-stack we will be deploying Logstash on an Amazon EC2 instance.

```bash
cdk deploy elkk-logstash
```

![ELKK Logstash 1](/img/elkk_logstash_idx_1.png)

An Amazon EC2 instance is deployed with Logstash installed and configured with an input from Kafka and output to Elasticsearch and s3.

![ELKK Logstash 2](/img/elkk_logstash_idx_2.png)

Wait until 2/2 checks are completed on the Logstash EC2 instance to ensure that the userdata scripts have fully run.  

![ELKK Logstash 3](/img/elkk_logstash_idx_3.png)

Connect to the Logstash EC2 instance using a terminal window:  

```bash
# get the logstash instance public dns
logstash_dns=`aws ec2 describe-instances --filter file://logstash/logstash_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $logstash_dns
# use the public dns to connect to the logstash instance
ssh ec2-user@$logstash_dns
```

![ELKK Logstash 4](/img/elkk_logstash_idx_4.png)

While connected to logstash EC2 instance:

```bash
# verify the logstash config, the last line should contain "Config Validation Result: OK. Exiting Logstash"
/usr/share/logstash/bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/logstash.conf
# check the logstash status
service logstash status -l
```

![ELKK Logstash 5](/img/elkk_logstash_idx_5.png)

Exit the Logstash instance and reconnect to the Filebeat instance.

```bash
# exit logstash instance
exit
# get the Filebeat ec2 instance public dns
filebeat_dns=`aws ec2 describe-instances --filter file://filebeat/filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat ec2 instance
ssh ec2-user@$filebeat_dns
```

In the Filebeat EC2 instance generate new log files.

```bash
# generate new logs
./log_generator.py
```

![ELKK Logstash 6](/img/elkk_logstash_idx_6.png)

Navigate to Kibana and view the logs generated.

Create a new Index Pattern for the apache logs using pattern "elkk-apachelog*". 

![ELKK Logstash 7](/img/elkk_logstash_idx_7.png)

At the Configure Settings dialog there is now an option to select a timestamp. Select "@timestamp".

![Dashboard](/img/elkk_logstash_idx_8.png)

Apache Logs will now appear on a refreshed Dashboard by their timestamp. Apache Logs are selected by their index at mid-left of the Dashboard.

![Dashboard](/img/elkk_logstash_idx_9.png)

Navigate to s3 to view the files pushed to s3.

![Dashboard](/img/elkk_logstash_idx_10.png)

![Dashboard](/img/elkk_logstash_idx_11.png)

Logstash can be deployed into containers or virtual machines. To deploy logstash on containers update the logstash deployment from Amazon EC2 to AWS Fargate.

Update the [/app.py](/app.py) file and verify that the elkk-logstash stack is set to fargate and not ec2.

```python
# logstash stack
logstash_stack = LogstashStack(
    app,
    "elkk-logstash",
    vpc_stack,
    logstash_ec2=False,
    logstash_fargate=True,
    env=core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_ACCOUNT"],
    ),
)
```

Deploy the updated stack, terminating the Logstash EC2 instance and creating a Logstash service on AWS Fargate.

```bash
cdk deploy elkk-logstash
```

![Logstash 12](/img/elkk_logstash_idx_12.png)

The logstash EC2 instance will be terminated and an AWS Fargate cluster will be created. Logstash will be deployed as containerized tasks.

![Logstash 13](/img/elkk_logstash_idx_13.png)

In the Filebeat EC2 instance generate new logfiles.

```bash
# get the Filebeat ec2 instance public dns
filebeat_dns=`aws ec2 describe-instances --filter file://filebeat/filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat ec2 instance
ssh ec2-user@$filebeat_dns

```bash
# generate new logs, the -f 20 will generate 20 files at 30 second intervals
./log_generator.py -f 20
```

![Logstash 14](/img/elkk_logstash_idx_14.png)

Navigate to Kibana and view the logs generated. They will appear in the Dashboard for Apache Logs as they are generated.

![Dashboard](/img/kibana_idx_8.png)

-----
## Cleanup <a name=cleanup></a>

To clean up the stacks... destroy the elkk-vpc stack, all other stacks will be torn down due to dependencies. 

CloudWatch logs will need to be separately removed.

```bash
cdk destroy elkk-vpc
```

![Destroy](/img/destroy_idx_1.png)

## License

This library is licensed under the MIT-0 License. See the LICENSE file.