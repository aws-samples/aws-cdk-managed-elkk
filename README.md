# Amazon Managed ELKK
 
This repository contains an implimentation example of a managed ELKK stack using the AWS Cloud Development Kit. This example uses Python.

## Table of Contents
1. [Context](#context)
2. [Prerequisites](#prerequisites)
3. [Amazon Virtual Private Cloud](#vpc)
4. [Amazon Managed Streaming for Apache Kafka](#kafka)
5. [Filebeat](#filebeat)
6. [Amazon Elasticsearch Service](#elastic)
7. [Amazon Athena](#athena)
8. [Logstash](#logstash)
9. [Clean up](#cleanup)

## Context <a name="context"></a>

The ELKK stack is a pipeline of services to support real-time reporting and analytics. Amazon services can provide a managed ELKK stack using the services Amazon Elasticsearch Service, Logstash on Amazon EC2 or on Amazon Elastic Container Services and Amazon Managed Streaming for Kafka. Kibana is included as a capability of the Amazon Elasticsearch Service. As part of a hoslistic solution Logstash in addition to outputing logs to Amazon Elasticsearch outputs the log to Amazon S3 for longer term storage. Amazon Athena can be used to directly query files in Amazon S3.

### Components

Filebeat agents will be used to collect the logs from the application/host systems, and publish the logs to Amazon MSK. Filebeat agents are deployed on an Amazon EC2 instance to simulate log generation.

Amazon Managed Streaming for Kafka (Amazon MSK) is used as a buffering layer to handle the collection of logs and manage the back-pressure from downstream components in the architecture. The buffering layer will provide recoverability and extensibility in the platform.

The Logstash layer will perform a dual-purpose of reading the data from Amazon MSK and indexing the logs to Amazon Elasticsearch in real-time as well as storing the data to S3.

Users can search for logs in Amazon Elasticsearch Service using Kibana front-end UI application. Amazon Elasticsearch is a fully managed service which provides a rich set of features such as Dashboards, Alerts, SQL query support and much more which can be used based on workload specific requirements.

Logs are stored in Amazon S3 to support cold data log analysis requirements. AWS Glue catalog will store the metadata information associated with the log files to be made available to the user for ad-hoc analysis.

Amazon Athena supports SQL queries against log data stored in Amazon S3.

![ELKK Architecture](elkk_architecture.png)

-----
## Prerequisites <a name="prerequisites"></a>

The following tools are required to deploy this Amazon Managed ELKK stack.

AWS CDK - https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html  
AWS CLI - https://aws.amazon.com/cli/  
Git -  https://git-scm.com/downloads  
python (3.6 or later) - https://www.python.org/downloads/  
Docker - https://www.docker.com/  

Terminal commands in this README are designed for a bash client.

### Set up the Environment

Clone the Git repository, create the python environment and install the python dependancies.

```bash
# clone the repo
git clone https://github.com/fmcmac/elk-stack.git managed_elkk
# move to directory
cd managed_elkk
# create the virtual environment
python -m venv .env
# activate the virtual environment
source .env/bin/activate
# download requirements
pip install -r requirements.txt
```

Create the EC2 SSH key pair allowing connections to Amazon EC2 instances.

```bash
# create the key pair
aws ec2 create-key-pair --key-name $yourkeypair --query 'KeyMaterial' --output text > $yourkeypair.pem --region $yourregion
# update key_pair permissions
chmod 400 $yourkeypair.pem
# move key_pair to .ssh
mv $yourkeypair.pem $HOME/.ssh/$yourkeypair.pem
```

Run all terminal commonds from the project root directory.

### Boostrap the CDK

Create the CDK configuration by bootstrapping the CDK.

```bash
# bootstrap the cdk
cdk bootstrap aws://$youraccount/$yourregion
```

-----
## Amazon Virtual Private Cloud <a name="vpc"></a>

The first stage in the ELKK deployment is to create an Amazon Virtual Private Cloud with public and private subnets. The ELKK deployment will be into this VPC.

Use the AWS CDK to deploy an Amazon VPC across multiple availability zones.

```bash
# deploy the vpc stack
cdk deploy elkk-vpc
```

-----
## Amazon Managed Streaming for Apache Kafka <a name="kafka"></a>

The second stage in the ELKK deployment is to create the Amazon Managed Streaming for Apache Kafka cluster. An Amazon EC2 instance is created with the Apache Kafka client installed to interact with the Amazon MSK cluster.

Use the AWS CDK to deploy an Amazon MSK Cluster into the VPC.

```bash
# deploy the kafka stack
cdk deploy elkk-kafka
```

When Client is set to True an Amazon EC2 instance is deployed to interact with the Amazon MSK Cluster. It can take up to 30 minutes for the Amazon MSK cluster to be deployed.

Wait until 2/2 checks are completed on the Kafka client instance to ensure that the userdata scripts have fully run.  

From a terminal window connect to the Kafka client instance to create a producer session:  

```bash
# get the instance public dns
kafka_client_dns=`aws ec2 describe-instances --filter file://kafka/kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the instance
ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client instance create the producer session:

```bash
# Get the cluster ARN
kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a producer 
/opt/kafka_2.12-2.4.0/bin/kafka-console-producer.sh --broker-list $kafka_brokers --topic elkstacktopic
```

Leave the Kafka producer window open.  

From a new terminal window connect to the Kafka client instance to create consumer session:  

```bash
# get the instance public dns
kafka_client_dns=`aws ec2 describe-instances --filter file://kafka/kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the instance
ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client instance create the consumer session:

```bash
# Get the cluster ARN
kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a consumer
/opt/kafka_2.12-2.4.0/bin/kafka-console-consumer.sh --bootstrap-server $kafka_brokers --topic elkstacktopic --from-beginning
```

Leave the Kafka consumer window open.  

Messages typed into the Kafka producer window should appear in the Kafka consumer window.  

-----
## Filebeat <a name=filebeat></a>

To simulate incoming logs for the ELKK cluster Filebeat will be installed on an Amazon EC2 instance. Filebeat is configured to read logs generated by a log generator installed on the EC2 instance and push the logs to the Amazon MSK cluster.

Use the AWS CDK to create an Amazon EC2 instance installed with filebeat and a dummy log generator.

```bash
# deploy the filebeat stack
cdk deploy elkk-filebeat
```

An Amazon EC2 instance is deployed with Filebeat installed and configured to output to Kafka.  

Wait until 2/2 checks are completed on the Filebeat instance to ensure that the userdata script as run.

From a new terminal window connect to the Filebeat instance to create create dummy logs:

```bash
# get the filebeat instance public dns
filebeat_dns=`aws ec2 describe-instances --filter file://filebeat/filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat instance
ssh ec2-user@$filebeat_dns
```

While connected to the Filebeat instance create dummy logs:

```bash
# generate dummy logs with log builder
./log_generator.py
```

Messages generated by the log generator should appear in the Kafka consumer terminal window.

-----
## Amazon Elasticsearch Service <a name=elastic></a>

The Amazon Elasticsearch Service provides an Elasticsearch domain and Kibana dashboards. The elkk-elastic stack also creats an Amazon EC2 instance to interact with the Elasticsearch domain. The instance can also be used to create an SSH tunnel into the VPC for Kibana dashboard viewing.

```bash
# deploy the elastic stack
cdk deploy elkk-elastic
```

An Amazon EC2 instance is deployed to interact with the Amazon Elasticsearch Service domain.

New Amazon Elasticsearch Service domains take about ten minutes to initialize.

Wait until 2/2 checks are completed on the Amazon EC2 instance to ensure that the userdata script has run.

Connect to the EC2 instance using a terminal window:

```bash
# get the elastic instance public dns
elastic_dns=`aws ec2 describe-instances --filter file://elastic/elastic_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $elastic_dns
# use the public dns to connect to the elastic instance
ssh ec2-user@$elastic_dns
```

While connected to the Elastic Instance:

```bash
# get the elastic domain
elastic_domain=`aws es list-domain-names --output text --query '*'` && echo $elastic_domain
# get the elastic endpoint
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --output text --query 'DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# curl a doc into elasticsearch
curl -XPOST $elastic_endpoint/elkstack-test/_doc/ -d '{"director": "Burton, Tim", "genre": ["Comedy","Sci-Fi"], "year": 1996, "actor": ["Jack Nicholson","Pierce Brosnan","Sarah Jessica Parker"], "title": "Mars Attacks!"}' -H 'Content-Type: application/json'
# curl to query elasticsearch
curl -XPOST $elastic_endpoint/elkstack-test/_search -d' { "query": { "match_all": {} } }' -H 'Content-Type: application/json'
# count the records in the index
curl -GET $elastic_endpoint/elkstack-test/_count
# exit the Elastic instance
exit
```

Create an SSH tunnel to Kibana.

```bash
# get the elastic instance public dns
elastic_dns=`aws ec2 describe-instances --filter file://elastic/elastic_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $elastic_dns
# get the elastic domain
elastic_domain=`aws es list-domain-names --output text --query '*'` && echo $elastic_domain
# get the elastic endpoint
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --output text --query 'DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# create the tunnel
ssh ec2-user@$elastic_dns -N -L 9200:$elastic_endpoint:443 -4
```

Leave the tunnel terminal window open.

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana.

-----
## Amazon Athena <a name=athena></a>

Amazon Simple Storage Service is used to storage logs for longer term storage. Amazon Athena can be used to query files on S3. 

```bash
# deploy the athena stack
cdk deploy elkk-athena
```

-----
## Logstash <a name=logstash></a>

Logstash is deployed to subsribe to the Kafka topics and output the data into Elasticsearch. An additional output is added to push the data into S3. Logstash additionally parses the apache common log format and transforms the log data into json format.

Deploy logstash first on an Amazon EC2 instance.

Check the app.py file and verify that the elkk-logstash stack is initially set to create logstash on ec2 and not on fargate.

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

When we deploy the elkk-stack we will be deploying logstash on ec2.

```bash
cdk deploy elkk-logstash
```

An Amazon EC2 instance is deployed with Logstash installed and configured with an input from Kafka and output to Elasticsearch and s3.

Wait until 2/2 checks are completed on the Logstash instance to ensure that the userdata scripts have fully run.  

Connect to the Logstash Instance using a terminal window:  

```bash
# get the logstash instance public dns
logstash_dns=`aws ec2 describe-instances --filter file://logstash/logstash_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $logstash_dns
# use the public dns to connect to the logstash instance
ssh ec2-user@$logstash_dns
```

While connected to logstash instance:

```bash
# verify the logstash config
/usr/share/logstash/bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/logstash.conf
# check the logstash status
service logstash status -l
# if logstash isn't running then restart it
service logstash start
```

In the Filebeat Instance generate new logfiles

```bash
# geneate new logs
./log_generator.py
```

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana and view the logs generated.  

Navigate to s3 to view the files pushed to s3.

Logstash can be deployed into containers or virtual machines. To deploy logstash on containers update the logstash deployment from Amazon ec2 to AWS Fargate.

Update the app.py file and verify that the elkk-logstash stack is set to fargate and not ec2.

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

The logstash ec2 instance will be terminated and an AWS Fargate cluster will be created. Logstash will be deployed as containerized tasks.

In the Filebeat Instance generate new logfiles.

```bash
# geneate new logs
./log_generator.py
```

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana and view the logs generated.

Navigat to s3 to view the files pushed into s3.

-----
## Cleanup <a name=cleanup></a>

To clean up the stacks... destroy the elkk-vpc stack, all other stacks will be torn down due to dependancies. 

Cloudwatch logs will need to be separately removed.

```bash
cdk destroy elkk-vpc
```
