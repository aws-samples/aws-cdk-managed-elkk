#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# set elk_region region as env variable
# export AWS_DEFAULT_REGION=$elk_region
echo "export AWS_DEFAULT_REGION=$elk_region" >> /etc/profile
# get python3
yum install python3 -y
# get pip
yum install python-pip -y
# make log generator executable
chmod +x /home/ec2-user/log_generator.py 
# get log generator requirements
python3 -m pip install -r /home/ec2-user/requirements.txt

# filebeat
rpm --import https://packages.elastic.co/GPG-KEY-elasticsearch
# move filebeat repo file
mv -f /home/ec2-user/elastic.repo /etc/yum.repos.d/elastic.repo
# install filebeat
yum install filebeat -y
# move filebeat.yml to final location
mv -f /home/ec2-user/filebeat.yml /etc/filebeat/filebeat.yml

# ownership
chown -R ec2-user:ec2-user /home/ec2-user

# start filebeat
systemctl start filebeat
systemctl enable filebeat
systemctl status filebeat
# complete
echo Complete setup script