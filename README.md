# Amazon Managed ELKK
 
This repository contains an implimentation example of a managed ELKK stack using the AWS Cloud Development Kit. This example uses Python.

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

The ELKK stack is a pipeline of services to support real-time reporting and analytics. Amazon services can provide a managed ELKK stack using the services Amazon Elasticsearch Service, Logstash on Amazon EC2 or on Amazon Elastic Container Services and Amazon Managed Streaming for Kafka. Kibana is included as a capability of the Amazon Elasticsearch Service. As part of a hoslistic solution Logstash in addition to outputing logs to Amazon Elasticsearch outputs the log to Amazon S3 for longer term storage. Amazon Athena can be used to directly query files in Amazon S3.

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

If not using AWS Cloud9 skip to section "Create the Managed ELKK".

### AWS Cloud9 - Create Cloud9 Environment

AWS Cloud9 is a cloud-based integrated development environment (IDE) that lets you write, run, and debug your code with just a browser. All of the prerequisites for the Managed ELKK are installed in a Cloud9 Environment.

Open the Cloud9 console: https://console.aws.amazon.com/cloud9

On the Cloud9 home page:

* Click: "Create Environment"

![Cloud 9 - Create Environment](/img/cloud9_idx_1.png)

On the "Name environment" screen:

* Input "Name" = "elkk-workshop".
* Click "Next Step".

![Cloud 9 - Name Environment](/img/cloud9_idx_2.png)

On the "Configure settings" screen:

* Select "Environment type" = "Create a new instance for environment (EC2)"
* Select "Instance Type" = "t3.small (2 GiB RAM + 2 vCPU)"
* Select "Platform" = "Amazon Linux"

![Cloud 9 - Name Environment](/img/cloud9_idx_3.png)

* Click "Next Step"

![Cloud 9 - Name Environment](/img/cloud9_idx_4.png)

On the "Review" screen:

* Review the settings
* Click "Create Environment"

![Cloud 9 - Name Environment](/img/cloud9_idx_5.png)

Cloud9 will report: "We are creating your AWS Cloud9 environment. This can take a few minutes."

![Cloud 9 - Name Environment](/img/cloud9_idx_6.png)

The Cloud9 instance will need some additional size for the Managed ELKK project. To increase the Amazon EBS volume to 50GB complete the following steps (additional details can be found at: https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html).

Create a new file in Cloud9:

![Cloud 9 - New fileame](/img/cloud9_idx_7.png)

Paste in the below content and save the file.

```sh
#!/bin/bash

# Specify the desired volume size in GiB as a command-line argument. If not specified, default to 20 GiB.
SIZE=${1:-20}

# Install the jq command-line JSON processor.
sudo yum -y install jq

# Get the ID of the envrionment host Amazon EC2 instance.
INSTANCEID=$(curl http://169.254.169.254/latest/meta-data//instance-id)

# Get the ID of the Amazon EBS volume associated with the instance.
VOLUMEID=$(aws ec2 describe-instances --instance-id $INSTANCEID | jq -r .Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId)

# Resize the EBS volume.
aws ec2 modify-volume --volume-id $VOLUMEID --size $SIZE

# Wait for the resize to finish.
while [ "$(aws ec2 describe-volumes-modifications --volume-id $VOLUMEID --filters Name=modification-state,Values="optimizing","completed" | jq '.VolumesModifications | length')" != "1" ]; do
  sleep 1
done

# Rewrite the partition table so that the partition takes up all the space that it can.
sudo growpart /dev/xvda 1

# Expand the size of the file system.
sudo resize2fs /dev/xvda1
```

![Cloud 9 - Save fileame](/img/cloud9_idx_8.png)

Save the file as "resize.sh".

![Cloud 9 - Save As](/img/cloud9_idx_9.png)

Execute the size script with the command:

```bash
sh resize.sh 50
```

![Cloud 9 - Execute resize](/img/cloud9_idx_10.png)

The Cloud9 instance needs to be rebooted for the resize to be effected. Run the command below:

```bash
sudo reboot
```

![Cloud 9 - Reboot](/img/cloud9_idx_11.png)

Cloud9 will restart, wait a few minutes and then refresh the page.

![Cloud 9 - Wait](/img/cloud9_idx_12.png)

### Create the Managed ELKK 


Recommence here if not using AWS Cloud9.

Complete the following steps to set up the Managed ELKK workshop in your environment.

At a bash terminal session.

![Terminal - Clone the repo](/img/create_elkk_idx_1.png)

```bash
# clone the repo
$ git clone https://github.com/fmcmac/elk-stack.git managed_elkk
# move to directory
$ cd managed_elkk
# create the virtual environment
$ python -m venv .env
# activate the virtual environment
$ source .env/bin/activate
```

![Terminal - Activate ENV](/img/activate_env_idx_1.png)

```bash
# download requirements
(.env)$ python -m pip install -r requirements.txt
```

Create the EC2 SSH key pair allowing connections to Amazon EC2 instances.

In all commands update "yourkeypair" with your chosen key pair name, and "yourregion" with your region name.

```bash
# create the key pair (note that the key-name has no .pem, output text has .pem at the end)
(.env)$ aws ec2 create-key-pair --key-name yourkeypair --query 'KeyMaterial' --output text > yourkeypair.pem --region yourregion
# update key_pair permissions
(.env)$ chmod 400 yourkeypair.pem
# move key_pair to .ssh
(.env)$ mv yourkeypair.pem $HOME/.ssh/yourkeypair.pem
# start the ssh agent
(.env)$ eval `ssh-agent -s`
# add your key to keychain
(.env)$ ssh-add -k ~/.ssh/yourkeypair.pem 
```

The file helpers/constants.py contains configuration for the Managed ELKK stack. This configuration can be left as default, except for the KEY_PAIR value which needs to be updated to your key pair name.

Update the [/helpers/constants.py](/helpers/constants.py) file with your key pair name:

```python
constants = {
    # project level constants
    "PROJECT_TAG": "elkk-stack",
    # do not include the .pem in the keypair name
    "KEY_PAIR": "yourkeypair",
    # kafka settings
    # etc
    # etc
    # etc
}
```

![Terminal - Update constants.py](/img/constants_py_idx_1.png)

### Boostrap the CDK

Create the CDK configuration by bootstrapping the CDK.

```bash
# bootstrap the cdk
(.env)$ cdk bootstrap aws://youraccount/yourregion
```

-----
## Amazon Virtual Private Cloud <a name="vpc"></a>

The first stage in the ELKK deployment is to create an Amazon Virtual Private Cloud with public and private subnets. The Managed ELKK stack will be deployed into this VPC.

Use the AWS CDK to deploy an Amazon VPC across multiple availability zones.

```bash
# deploy the vpc stack
(.env)$ cdk deploy elkk-vpc
```

-----
## Amazon Managed Streaming for Apache Kafka <a name="kafka"></a>

The second stage in the ELKK deployment is to create the Amazon Managed Streaming for Apache Kafka cluster. An Amazon EC2 instance is created with the Apache Kafka client installed to interact with the Amazon MSK cluster.

Use the AWS CDK to deploy an Amazon MSK Cluster into the VPC.

```bash
# deploy the kafka stack
(.env)$ cdk deploy elkk-kafka
```

When Client is set to True an Amazon EC2 instance is deployed to interact with the Amazon MSK Cluster. It can take up to 30 minutes for the Amazon MSK cluster and client EC2 instance to be deployed.

Wait until 2/2 checks are completed on the Kafka client EC2 instance to ensure that the userdata scripts have fully run.

On creation the Kafka client EC2 instance will create three Kafka topics: "elkktopic", "apachelog", and "appevent".

Open a terminal window to connect to the Kafka client Amazon EC2 instance and create a Kafka producer session:

```bash
# get the ec2 instance public dns
(.env)$ kafka_client_dns=`aws ec2 describe-instances --filter file://kafka/kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the amazon ec2 instance
(.env)$ ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client EC2 instance create the Kafka producer session on the elkktopic Kafka topic:

```bash
# Get the cluster ARN
$ kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
$ kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a producer on the Kakfa topic "elkktopic" 
$ /opt/kafka_2.12-2.4.0/bin/kafka-console-producer.sh --broker-list $kafka_brokers --topic elkktopic
```

Leave the Kafka producer session window open.  

Open a terminal window and connect to the Kafka client EC2 instance to create a Kafka consumer session:  

```bash
# get the ec2 instance public dns
(.env)$ kafka_client_dns=`aws ec2 describe-instances --filter file://kafka/kafka_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}[0].Instance"` && echo $kafka_client_dns
# use the public dns to connect to the ec2 instance
(.env)$ ssh ec2-user@$kafka_client_dns
```

While connected to the Kafka client EC2 instance create the consumer session on the elkktopic Kafka topic.

```bash
# Get the cluster ARN
$ kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
$ kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a consumer
$ /opt/kafka_2.12-2.4.0/bin/kafka-console-consumer.sh --bootstrap-server $kafka_brokers --topic elkktopic --from-beginning
```

Leave the Kafka consumer session window open.

Type messages into the Kakfa producer session and they are published to the Amazon MSK cluster

The messages published to the Amazon MS cluster by the producer session will appear in the Kafka consumer window as they are read from the cluster.

The Kafka client EC2 instance windows can be closed.

-----
## Filebeat <a name=filebeat></a>

To simulate incoming logs for the ELKK cluster Filebeat will be installed on an Amazon EC2 instance. Filebeat will harvest logs generated by a dummy log generator and push these logs to the Amazon MSK cluster.

Use the AWS CDK to create an Amazon EC2 instance installed with Filebeat and a dummy log generator.

```bash
# deploy the Filebeat stack
(.env)$ cdk deploy elkk-filebeat
```

An Amazon EC2 instance is deployed with Filebeat installed and configured to output to Kafka.  

Wait until 2/2 checks are completed on the Filebeat EC2 instance to ensure that the userdata script as run.

Open a new terminal window connect to the Filebeat EC2 instance and create create dummy logs:

```bash
# get the Filebeat ec2 instance public dns
(.env)$ filebeat_dns=`aws ec2 describe-instances --filter file://filebeat/filebeat_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $filebeat_dns
# use the public dns to connect to the filebeat ec2 instance
(.env)$ ssh ec2-user@$filebeat_dns
```

While connected to the Filebeat EC2 instance create dummy logs:

```bash
# generate dummy apache logs with log generator
$ ./log_generator.py
```

Dummy logs created by the log generator will be written to the apachelog folder. Filebeat will harvest the logs and publish them to the Amazon MSK cluster.

In the Kafka client EC2 instance terminal window disconnect the consumer session with <control+c>.

Create Kafka consumer session on the apachelog Kafka topic.

```bash
# Get the cluster ARN
$ kafka_arn=`aws kafka list-clusters --output text --query 'ClusterInfoList[*].ClusterArn'` && echo $kafka_arn
# Get the bootstrap brokers
$ kafka_brokers=`aws kafka get-bootstrap-brokers --cluster-arn $kafka_arn --output text --query '*'` && echo $kafka_brokers
# Connect to the cluster as a consumer
$ /opt/kafka_2.12-2.4.0/bin/kafka-console-consumer.sh --bootstrap-server $kafka_brokers --topic apachelog --from-beginning
```

Messages generated by the log generator should appear in the Kafka consumer terminal window.

-----
## Amazon Elasticsearch Service <a name=elastic></a>

The Amazon Elasticsearch Service provides an Elasticsearch domain and Kibana dashboards. The elkk-elastic stack also creats an Amazon EC2 instance to interact with the Elasticsearch domain. The EC2 instance can also be used to create an SSH tunnel into the VPC for Kibana dashboard viewing.

```bash
# deploy the elastic stack
(.env)$ cdk deploy elkk-elastic
```

An Amazon EC2 instance is deployed to interact with the Amazon Elasticsearch Service domain.

New Amazon Elasticsearch Service domains take about ten minutes to initialize.

Wait until 2/2 checks are completed on the Amazon EC2 instance to ensure that the userdata script has run.

Connect to the EC2 instance using a terminal window:

```bash
# get the elastic ec2 instance public dns
(.env)$ elastic_dns=`aws ec2 describe-instances --filter file://elastic/elastic_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $elastic_dns
# use the public dns to connect to the elastic ec2 instance
(.env)$ ssh ec2-user@$elastic_dns
```

While connected to the Elastic EC2 instance:

```bash
# get the elastic domain
$ elastic_domain=`aws es list-domain-names --output text --query '*'` && echo $elastic_domain
# get the elastic endpoint
$ elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --output text --query 'DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# curl a doc into elasticsearch
$ curl -XPOST $elastic_endpoint/elkktopic/_doc/ -d '{"director": "Burton, Tim", "genre": ["Comedy","Sci-Fi"], "year": 1996, "actor": ["Jack Nicholson","Pierce Brosnan","Sarah Jessica Parker"], "title": "Mars Attacks!"}' -H 'Content-Type: application/json'
# curl to query elasticsearch
$ curl -XPOST $elastic_endpoint/elkktopic/_search -d' { "query": { "match_all": {} } }' -H 'Content-Type: application/json'
# count the records in the index
$ curl -GET $elastic_endpoint/elkktopic/_count
# exit the Elastic ec2 instance
$ exit
```

Amazon Elasticsearch Service has been deployed within a VPC in a private subnet. To accss Kibana we need to create a tunnel into the private subnet.

Create an SSH tunnel to Kibana.

```bash
# get the elastic ec2 instance public dns
(.env)$ elastic_dns=`aws ec2 describe-instances --filter file://elastic/elastic_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $elastic_dns
# get the elastic domain
(.env)$ elastic_domain=`aws es list-domain-names --output text --query '*'` && echo $elastic_domain
# get the elastic endpoint
(.env)$ elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --output text --query 'DomainStatus.Endpoints.vpc'` && echo $elastic_endpoint
# create the tunnel
(.env)$ ssh ec2-user@$elastic_dns -N -L 9200:$elastic_endpoint:443 -4
```

Leave the tunnel terminal window open.

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana.

-----
## Kibana <a name=kibana></a>

Kibana is deployed on the Amazon Elasticsearch Service within the VPC. To allow connections to the Kibana dashboard deploy a public endpoint using Amazon API Gateway, AWS Lambda, Amazon Cloudfront, and Amazon S3.

```bash
# deploy the kibana endpoint
(.env)$ cdk deploy elkk-kibana
```

The Kibana url is output by the AWS CDK as "elkk-kibana.kibanalink. Click on the link to nativate to Kibana.

To view the records on the Kibana dashboard an "index pattern" needs to be created.

Select "Management" on the left of the Kibana Dashboard.

![Select Managment](/img/kibana_idx_1.png)

Select "Index Patterns" at the top left of the Management Screen.

![Select Index Patterns](/img/kibana_idx_2.png)

Input an Index Patterns into the Index Pattern field as "elkktopc*".

![Input Pattern](/img/kibana_idx_3.png)

Click "Next Step".

Click "Create Index Pattern".

The fields from the index can be seen. Click on "Discover".

![Select Discover](/img/kibana_idx_4.png)

The data can be seen on the Discovery Dashboard.

![Dashboard](/img/kibana_idx_5.png)

-----
## Amazon Athena <a name=athena></a>

Amazon Simple Storage Service is used to storage logs for longer term storage. Amazon Athena can be used to query files on S3. 

```bash
# deploy the athena stack
(.env)$ cdk deploy elkk-athena
```

-----
## Logstash <a name=logstash></a>

Logstash is deployed to subsribe to the Kafka topics and output the data into Elasticsearch. An additional output is added to push the data into S3. Logstash additionally parses the apache common log format and transforms the log data into json format.

The Logstash pipeline configuration can be viewed in [logstash/logstash.conf](/logstash/logstash.conf)

Check the [/app.py](/app.py) file and verify that the elkk-logstash stack is initially set to deploy Logstash on an Amazon EC2 instance and Amazon Fargate deployent is disabled.

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
(.env)$ cdk deploy elkk-logstash
```

An Amazon EC2 instance is deployed with Logstash installed and configured with an input from Kafka and output to Elasticsearch and s3.

Wait until 2/2 checks are completed on the Logstash EC2 instance to ensure that the userdata scripts have fully run.  

Connect to the Logstash EC2 instance using a terminal window:  

```bash
# get the logstash instance public dns
$ logstash_dns=`aws ec2 describe-instances --filter file://logstash/logstash_filter.json --output text --query "Reservations[*].Instances[*].{Instance:PublicDnsName}"` && echo $logstash_dns
# use the public dns to connect to the logstash instance
$ ssh ec2-user@$logstash_dns
```

While connected to logstash EC2 instance:

```bash
# verify the logstash config, the last line should contain "Config Validation Result: OK. Exiting Logstash"
$ /usr/share/logstash/bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/logstash.conf
# check the logstash status
$ service logstash status -l
```

In the Filebeat EC2 instance generate new logfiles

```bash
# geneate new logs
$ ./log_generator.py
```

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana and view the logs generated.

Create a new Index Pattern for the apache logs using pattern "elkk-apachelog*". At the Configure Settings dialog there is now an option to select a timestamp. Select "@timestamp".

![Dashboard](/img/kibana_idx_6.png)

Apache Logs will now appear on a refreshed Dashboard by their timestamp. Apache Logs are selected by their index at mid-left of the Dashboard.

![Dashboard](/img/kibana_idx_7.png)

Navigate to s3 to view the files pushed to s3.

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
(.env)$ cdk deploy elkk-logstash
```

The logstash EC2 instance will be terminated and an AWS Fargate cluster will be created. Logstash will be deployed as containerized tasks.

In the Filebeat EC2 instance generate new logfiles.

```bash
# geneate new logs, the -f 20 will generate 20 files at 30 second intervals
$ ./log_generator.py -f 20
```

Navigate to https://localhost:9200/_plugin/kibana/ to access Kibana and view the logs generated. They will appear in the Dashboard for Apache Logs as they are generated.

![Dashboard](/img/kibana_idx_8.png)

Navigat to s3 to view the files pushed into s3.

-----
## Cleanup <a name=cleanup></a>

To clean up the stacks... destroy the elkk-vpc stack, all other stacks will be torn down due to dependancies. 

Cloudwatch logs will need to be separately removed.

```bash
(.env)$ cdk destroy elkk-vpc
```
