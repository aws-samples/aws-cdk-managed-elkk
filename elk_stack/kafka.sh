#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# jq to process json from bash
yum install jq -y
# update java
yum install java-1.8.0 -y
# set elk_region region as env variable
echo "export AWS_DEFAULT_REGION=$elk_region" >> /etc/profile

# install kakfa
wget https://www-us.apache.org/dist/kafka/$kafka_version/$kafka_download_version.tgz
tar -xvf $kafka_download_version.tgz
mv $kafka_download_version /opt
rm $kafka_download_version.tgz

# move client.properties to correct location
mv -f /home/ec2-user/client.properties /opt/$kafka_download_version/bin/client.properties

# create the topic
/opt/$kafka_download_version/bin/kafka-topics.sh --create --zookeeper $kafka_zookeeper --replication-factor 3 --partitions 1 --topic $elk_topic

# update the certs file into correct location
cp /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.222.b10-0.amzn2.0.1.x86_64/jre/lib/security/cacerts /tmp/kafka.client.truststore.jks

# complete
echo Complete setup script