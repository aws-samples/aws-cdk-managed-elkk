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

# get elastic output to es
git clone https://github.com/awslabs/logstash-output-amazon_es.git /home/ec2-user/logstash-output-amazon_es

# logstash
rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# move logstash repo file
mv -f /home/ec2-user/logstash.repo /etc/yum.repos.d/logstash.repo
# get to the yum
yum install logstash -y
# add user to logstash group
usermod -a -G logstash ec2-user

# move logstash.yml to final location
mv -f /home/ec2-user/logstash.yml /etc/logstash/logstash.yml
# move logstash.conf to final location
mv -f /home/ec2-user/logstash.conf /etc/logstash/conf.d/logstash.conf
# move plugin 
mkdir /usr/share/logstash/plugins
mv -f /home/ec2-user/logstash-output-amazon_es /usr/share/logstash/plugins/logstash-output-amazon_es

# update gemfile
sed -i '5igem "logstash-output-amazon_es", :path => "/usr/share/logstash/plugins/logstash-output-amazon_es"' /usr/share/logstash/Gemfile
# update ownership
chown -R logstash:logstash /etc/logstash

# start logstash
sudo -u logstash systemctl start logstash.service

# complete
echo Complete setup script
