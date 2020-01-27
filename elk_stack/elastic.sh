#!/bin/bash

# start
echo Running setup script
# update packages
yum update -y
# jq to process json from bash
yum install jq -y

# complete
echo Complete setup script