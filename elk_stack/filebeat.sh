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
# move filebeat.yml to final location
mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml
# start filebeat
service filebeat start
# complete
echo Complete setup script