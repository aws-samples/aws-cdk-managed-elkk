#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# jq to process json from bash
yum install jq -y
# need git to install log generator
yum install git -y

# get log generator
git clone https://github.com/kiritbasu/Fake-Apache-Log-Generator.git /home/ec2-user/Fake-Apache-Log-Generator
chown -R ec2-user:ec2-user /home/ec2-user/Fake-Apache-Log-Generator
# get python packages
curl -O https://bootstrap.pypa.io/get-pip.py
python get-pip.py --user
python -m pip install -r /home/ec2-user/Fake-Apache-Log-Generator/requirements.txt
# create the dummy log output path
mkdir /home/ec2-user/log
chown -R ec2-user:ec2-user /home/ec2-user/log

# filebeat
rpm --import https://packages.elastic.co/GPG-KEY-elasticsearch
# move filebeat repo file
mv -f /home/ec2-user/elastic.repo /etc/yum.repos.d/elastic.repo
# install filebeat
yum install filebeat -y
# update filebeat with correct brokerstring
kafka_arn=`aws kafka list-clusters --region us-east-1 --output json --query 'ClusterInfoList[*].ClusterArn' | jq '.[0]' -r` && echo $kafka_arn
kafka_brokers=`aws kafka get-bootstrap-brokers --region us-east-1 --cluster-arn $kafka_arn --output json | jq -r '.BootstrapBrokerString' | sed 's/,/", "/g' | sed 's/^/\ "/' | sed 's/$/"\ /'` && echo $kafka_brokers
sed -i "s/kafka_brokers/$kafka_brokers/" /home/ec2-user/filebeat.yml
# move filebeat.yml to final location
mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml
# start filebeat
service filebeat start
# complete
echo Complete setup script