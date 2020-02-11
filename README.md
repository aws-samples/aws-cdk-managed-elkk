
# Building an ELKK Stack

Because: Filebeat > Kafka > Logstash > ElasticSearch > Kibana


![ELKK Architecture](elkk_architecture.png)

## Prerequisites

AWS CDK - https://docs.aws.amazon.com/cdk/index.html  
AWS CLI - https://aws.amazon.com/cli/  
Git -  https://git-scm.com/downloads  
python (3.6 or later) - https://www.python.org/downloads/  
jq - https://stedolan.github.io/jq/download/  

### Set up the Environment

Clone the Git repository, create the python environment and install the python dependancies.

```bash
# clone the repo
git clone https://github.com/fmcmac/elk-stack.git
# move to directory
cd elk-stack
# create the virtual environment
python -m venv .env
# activate the virtual environment
(MacOs) source .env/bin/activate
(Windows) .env\Scripts\activate.bat
# download requirements
pip install -r requirements.txt
```

```bash
# name the key pair
yourkeypair="yourkeypair"
yourregion="yourregion"
# create the key pair
aws ec2 create-key-pair --key-name $yourkeypair --query 'KeyMaterial' --output text > $yourkeypair.pem --region $yourregion
# update key_pair permissions
chmod 400 $yourkeypair.pem
# move key_pair to .ssh
mv $yourkeypair.pem $HOME/.ssh/ElkKeyPair.pem
# add ssh key to keychain
ssh-add ~/.ssh/$yourkeypair.pem
```

### Set the configuration

Create a file in the project "elk_stack" folder as "constants.py"  

Create the file content as below file with the correct region and account, ensure that the keypair name matches that used previously

```python
#!/usr/bin/env python3

# project level constants
ELK_PROJECT_TAG = "elk-stack"
ELK_KEY_PAIR = "yourkeypair"
ELK_REGION = "yourregion"
ELK_ACCOUNT = "youraccount"

# kafka settings
ELK_KAFKA_DOWNLOAD_VERSION = "kafka_2.12-2.4.0"
ELK_KAFKA_BROKER_NODES = 3
ELK_KAFKA_VERSION = "2.3.1"
ELK_KAFKA_INSTANCE_TYPE = "kafka.m5.large"
ELK_TOPIC = "elkstacktopic"
ELK_KAFKA_CLIENT_INSTANCE = "t2.xlarge"

# filebeat
ELK_FILEBEAT_INSTANCE = "t2.xlarge"

# elastic
ELK_ELASTIC_CLIENT_INSTANCE = "t2.xlarge"
ELK_ELASTIC_MASTER_COUNT = 3
ELK_ELASTIC_MASTER_INSTANCE = "r5.large.elasticsearch"
ELK_ELASTIC_INSTANCE_COUNT = 3
ELK_ELASTIC_INSTANCE = "r5.large.elasticsearch"
ELK_ELASTIC_VERSION = "7.1"

# logstash
ELK_LOGSTASH_INSTANCE = "t2.xlarge"
```

Run all terminal comments from the project root directory.

Confrim that the project is correctly set up.

```bash
cdk synth
```

### Boostrap the CDK

Create the CDK configuration bucket.

```bash
# bootstrap the cdk
cdk bootstrap aws://youraccount/$yourregion
```

### Amazon Virtual Private Cloud

Use the AWS CDK to deploy an Amazon VPC across multiple availability zones.

```bash
# deploy the vpc stack
cdk deploy elk-vpc
```

### Amazon Managed Streaming for Apache Kafka

Amazon Managed Streaming for Kafka (Amazon MSK) will be used as a buffering layer to handle the collection of logs and manage the back-pressure from downstream components in the architecture. The buffering layer will provide recoverability and extensibility in the platform.

Use the AWS CDK to deploy an Amazon MSK Cluster into the VPC.  

```bash
# deploy the kafka stack
cdk deploy elk-kafka
```

When Client is set to True an Amazon EC2 instance is deployed to interact with the Amazon MSK Cluster. It can take up to 30 minutes for the Amazon MSK cluster to be deployed.

Wait until 2/2 checks are completed on the Kafka client instance to ensure that the userdata scripts have fully run.  

From a terminal window connect to the Kafka client instance to create a producer session:  

```bash
# get the instance public dns
kafka_client_dns=`aws ec2 describe-instances --filter file://kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the instance
ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client instance create the producer session:

```bash
# Get the cluster ARN
kafka_arn=`aws kafka list-clusters --region us-east-1 --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
kafka_brokers=`aws kafka get-bootstrap-brokers --region us-east-1 --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a producer 
/opt/kafka_2.12-2.4.0/bin/kafka-console-producer.sh --broker-list $kafka_brokers --topic elkstacktopic
```

Leave the Kafka producer window open.  

From a new terminal window connect to the Kafka client instance to create consumer session:  

```bash
# get the instance public dns
kafka_client_dns=`aws ec2 describe-instances --filter file://kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the instance
ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client instance create the consumer session:

```bash
# Get the cluster ARN
kafka_arn=`aws kafka list-clusters --region us-east-1 --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
kafka_brokers=`aws kafka get-bootstrap-brokers --region us-east-1 --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a consumer
/opt/kafka_2.12-2.4.0/bin/kafka-console-consumer.sh --bootstrap-server $kafka_brokers --topic elkstacktopic --from-beginning
```

Leave the Kafka consumer window open.  

Messages typed into the Kafka producer window should appear in the Kafka consumer window.  

### Filebeats

Filebeat agents will be used to collect the logs from the application/host systems, and publish the logs to Amazon MSK.

Use the AWS CDK to create an Amazon EC2 instance installed with filebeat and a dummy log generator.

```bash
# deploy the filebeat stack
cdk deploy elk-filebeat
```

An Amazon EC2 instance is deployed with Filebeat installed and configured to output to Kafka.  

Wait until 2/2 checks are completed on the Filebeat instance to ensure that the userdata scripts have fully run.  

From a new terminal window connect to the Filebeat instance to create create dummy logs:  

```bash
# get the filebeat instance public dns
filebeat_dns=`aws ec2 describe-instances --filter file://filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat instance
ssh ec2-user@$filebeat_dns
```

While connected to the Filebeat instance create dummy logs:

```bash
# generate dummy logs with fake log builder
python ./Fake-Apache-Log-Generator/apache-fake-log-gen.py -n 10 -o LOG -p /home/ec2-user/log/ -l CLF
```

Messages generated by the Fake-Apache-Log-Generator should appear in the Kafka consumer terminal window.

### Amazon Elasticsearch Service

Users can search for logs in Amazon Elasticsearch Service using Kibana front-end UI application. Amazon Elasticsearch is a fully managed service which provides a rich set of features such as Dashboards, Alerts, SQL query support and much more which can be used based on workload specific requirements.

```bash
# deploy the elastic stack
cdk deploy elk-elastic
```

An Amazon EC2 instance is deployed to interact with the Elasticsearch Domain.   

New Elasticsearch take about ten minutes to initialize.  

Wait until 2/2 checks are completed on the Elastic ec2 instance to ensure that the userdata scripts have fully run.  

Connect to the Elastic Instance using a terminal window:  

```bash
# get the elastic instance public dns
elastic_dns=`aws ec2 describe-instances --filter file://elastic_filter.json --query "Reservations[*].Instances[*].{Instance:PublicDnsName}" --output json | jq -r '.[0][0].Instance'` && echo $elastic_dns
# use the public dns to connect to the elastic instance
ssh ec2-user@$elastic_dns
```

While connected to the Elastic Instance:

```bash
# get the elastic domain
elastic_domain=`aws es list-domain-names --region us-east-1 | jq '.DomainNames[0].DomainName' -r` && echo $elastic_domain
# get the elastic endpoint
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --region us-east-1 | jq -r '.DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
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
elastic_dns=`aws ec2 describe-instances --filter file://elastic_filter.json --query "Reservations[*].Instances[*].{Instance:PublicDnsName}" --output json | jq -r '.[0][0].Instance'` && echo $elastic_dns
# get the elastic domain
elastic_domain=`aws es list-domain-names --region us-east-1 | jq '.DomainNames[0].DomainName' -r` && echo $elastic_domain
# get the elastic endpoint
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --region us-east-1 | jq -r '.DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# create the tunnel
ssh ec2-user@$elastic_dns -N -L 9200:$elastic_endpoint:443
```

Leave the tunnel terminal window open.

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana.

## Amazon Athena

Amazon Athena supports SQL queries against log data stored in Amazon S3. Best practices related to partitioning of log data in the S3 storage with a suitable file storage format can help reduce the costs of querying the data from Athena.

Logs are stored in Amazon S3 to support cold data log analysis requirements. The log files can be stored in read-optimized file formats for faster query capabilities. AWS Glue catalog will store the metadata information associated with the log files to be made available to the user for ad-hoc analysis.


```bash
cdk deploy elk-athena
```

### Logstash

Logstash layer will perform a dual-purpose of reading the data from Amazon MSK and indexing the logs to Amazon Elasticsearch in real-time as well as archiving the data to S3. Auto-scaling on the Logstash nodes can be implemented to reduce costs.

```bash
cdk deploy elk-logstash
```

An Amazon EC2 instance is deployed with Logstash installed and configured with an input from Kafka and output to Elasticsearch.  

Wait until 2/2 checks are completed on the Logstash instance to ensure that the userdata scripts have fully run.  

Connect to the Logstash Instance using a terminal window:  

```bash
# get the logstash instance public dns
logstash_dns=`aws ec2 describe-instances --filter file://logstash_filter.json --query "Reservations[*].Instances[*].{Instance:PublicDnsName}" --output json | jq -r '.[0][0].Instance'` && echo $logstash_dns
# use the public dns to connect to the logstash instance
ssh ec2-user@$logstash_dns
```

While connected to logstash instance:

```bash
# confirm the conf file has the correct cluster and domain
cat /etc/logstash/conf.d/logstash.conf
# verify the logstash config
/usr/share/logstash/bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/logstash.conf
# check the logstash status
service logstash status -l
# if logstash isn't running then restart it
service logstash start
```

In the Filebeats Instance generate new logfiles

```bash
# geneate new logs
python ./Fake-Apache-Log-Generator/apache-fake-log-gen.py -n 10 -o LOG -p /home/ec2-user/log/ -l CLF
```

In Kibana view the new logs

### Cleanup Environment

To clean up the stacks... destroy the elk-vpc stack, all other stacks will be torn down due to dependancies.

```bash
cdk destroy elk-vpc
```
