#!/bin/bash

# create the virtual environment
python -m venv .env
# download requirements
.env/bin/python -m pip install -r requirements.txt
# create the key pair
aws ec2 create-key-pair --key-name yourkeypair --query 'KeyMaterial' --output text > yourkeypair.pem --region us-east-1
# update key_pair permissions
chmod 400 yourkeypair.pem
# move key_pair to .ssh
mv -f yourkeypair.pem $HOME/.ssh/yourkeypair.pem
# start the ssh agent
eval `ssh-agent -s`
# add your key to keychain
ssh-add -k ~/.ssh/yourkeypair.pem 