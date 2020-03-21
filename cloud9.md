# Cloud 9 Create Environment

Instructions for setting up the Managed ELKK environment when using Amazon Cloud9.

Start by opening the cloud9 console: https://console.aws.amazon.com/cloud9

On the Cloud9 home page:

* Click: "Create Environment"

On the "Name environment" screen:

* Input "Name" = "managed-elkk".
* Click "Next Step".

On the "Configure settings" screen:

* Select "Environment type" = "Create a new instance for environment (EC2)"
* Select "Instance Type" = "t3.small (2 GiB RAM + 2 vCPU)"
* Select "Platform" = "Amazon Linux"
* Click "Next Step"

On the "Review" screen:

* Review the settings
* Click "Create Environment"

Cloud9 will report: "We are creating your AWS Cloud9 environment. This can take a few minutes."

### Set up Managed ELKK

At a bash terminal.

```bash
# start from the environment directory
cd ~/environment
# clone the repo
git clone https://github.com/fmcmac/elk-stack.git managed_elkk
# move to directory
cd managed_elkk
# create the virtual environment
python -m venv .env
# activate the virtual environment
source .env/bin/activate
# download requirements
(.env)$ python -m pip install -r requirements.txt
```

Create the EC2 SSH key pair allowing connections to Amazon EC2 instances.

```bash
# create the key pair (note that the key-name has no .pem, output text has .pem at the end)
aws ec2 create-key-pair --key-name $yourkeypair --query 'KeyMaterial' --output text > $yourkeypair.pem --region $yourregion
# update key_pair permissions
chmod 400 $yourkeypair.pem
# move key_pair to .ssh
mv $yourkeypair.pem $HOME/.ssh/$yourkeypair.pem
# start the ssh agent
eval `ssh-agent -s`
# add your key to keychain
ssh-add -k ~/.ssh/$yourkeypair.pem 
```
####### done to here #######

The file helpers/constants.py contains configuration for the Managed ELKK stack. This configuration can be left as default, except for the KEY_PAIR value which needs to be updated to your key pair name.

Update the [/helpers/constants.py](/helpers/constants.py) file with your key pair name:

```python
constants = {
    # project level constants
    "PROJECT_TAG": "elkk-stack",
    # do not include the .pem in the keypair name
    "KEY_PAIR": "$yourkeypair",
    # kafka settings
    # etc
    # etc
    # etc
}
```

The file helpers/constants.py contains configuration for the Managed ELKK stack. This configuration can be left as default, except for the KEY_PAIR value which needs to be updated to your key pair name.

Run all terminal commonds from the project root directory.

### Boostrap the CDK