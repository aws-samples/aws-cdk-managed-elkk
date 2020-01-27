#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# jq to process json from bash
yum install jq -y
# install java
amazon-linux-extras install java-openjdk11 -y
# install git
yum install git -y

# get log generator
git clone https://github.com/awslabs/logstash-output-amazon_es.git /home/ec2-user/logstash-output-amazon_es

# logstash
rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# move logstash repo file
mv -f /home/ec2-user/logstash.repo /etc/yum.repos.d/logstash.repo
# get to the yum
yum install logstash -y
# add user to logstash group
usermod -a -G logstash ec2-user

# get domain details
elastic_domain=`aws es list-domain-names --region us-east-1 | jq '.DomainNames[0].DomainName' -r` && echo $elastic_domain
elastic_endpoint=`aws es describe-elasticsearch-domain --domain-name $elastic_domain --region us-east-1 | jq -r '.DomainStatus.Endpoints.vpc' | sed 's/^/\ "/' | sed 's/$/"\ /'` && echo $elastic_endpoint
sed -i "s/elastic_endpoint/$elastic_endpoint/" /home/ec2-user/logstash.conf
kafka_arn=`aws kafka list-clusters --region us-east-1 --output json --query 'ClusterInfoList[*].ClusterArn' | jq '.[0]' -r` && echo $kafka_arn
kafka_brokers=`aws kafka get-bootstrap-brokers --region us-east-1 --cluster-arn $kafka_arn --output json | jq -r '.BootstrapBrokerString' | sed 's/^/\ "/' | sed 's/$/"\ /'` && echo $kafka_brokers
sed -i "s/kafka_brokers/$kafka_brokers/" /home/ec2-user/logstash.conf

# move logstash.yml to final location
mv -f /home/ec2-user/logstash.yml /etc/logstash/logstash.yml
# move logstash.conf to final location
mv -f /home/ec2-user/logstash.conf /etc/logstash/conf.d/logstash.conf
# move plugin 
mkdir /usr/share/logstash/plugins
mv -f /home/ec2-user/logstash-output-amazon_es /usr/share/logstash/plugins/logstash-output-amazon_es

# update gemfile
sed -i '5igem "logstash-output-amazon_es", :path => "/usr/share/logstash/plugins/logstash-output-amazon_es"' /usr/share/logstash/Gemfile

# complete
echo Complete setup script
