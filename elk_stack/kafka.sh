#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# jq to process json from bash
yum install jq -y
# update java
yum install java-1.8.0 -y

# install kakfa
wget https://www-eu.apache.org/dist/kafka/2.4.0/kafka_2.12-2.4.0.tgz
tar -xvf kafka_2.12-2.4.0.tgz
mv kafka_2.12-2.4.0 /opt

# move client.properties to correct location
mv -f /home/ec2-user/client.properties /opt/kafka_2.12-2.4.0/bin/client.properties

# get zookeeper string from the cluster
kafka_arn=`aws kafka list-clusters --region us-east-1 --output json --query 'ClusterInfoList[*].ClusterArn' | jq '.[0]' -r` && echo $kafka_arn
kafka_zookeeper=`aws kafka describe-cluster --region us-east-1 --cluster-arn $kafka_arn --output json | jq -r '.ClusterInfo.ZookeeperConnectString'` && echo $kafka_zookeeper
# create the topic
/opt/kafka_2.12-2.4.0/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic elkstacktopic

# update the certs file into correct location
cp /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.222.b10-0.amzn2.0.1.x86_64/jre/lib/security/cacerts /tmp/kafka.client.truststore.jks

# complete
echo Complete setup script