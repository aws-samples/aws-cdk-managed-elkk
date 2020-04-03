# Cloud9 Setup for Amazon Managed ELKK

AWS Cloud9 is a cloud-based integrated development environment (IDE) that lets you write, run, and debug your code with just a browser. All of the prerequisites for the Managed ELKK are installed in a Cloud9 Environment.

Open the Cloud9 console: https://console.aws.amazon.com/cloud9

On the Cloud9 home page:

* Click: "Create Environment"

![Cloud 9 - Create Environment](/img/cloud9_idx_1.png)

On the "Name environment" screen:

* Input "Name" = "elkk-workshop".
* Click "Next Step".

![Cloud 9 - Name Environment](/img/cloud9_idx_2.png)

On the "Configure settings" screen:

* Select "Environment type" = "Create a new instance for environment (EC2)"
* Select "Instance Type" = "t3.small (2 GiB RAM + 2 vCPU)"
* Select "Platform" = "Amazon Linux"

![Cloud 9 - Name Environment](/img/cloud9_idx_3.png)

* Click "Next Step"

![Cloud 9 - Name Environment](/img/cloud9_idx_4.png)

On the "Review" screen:

* Review the settings
* Click "Create Environment"

![Cloud 9 - Name Environment](/img/cloud9_idx_5.png)

Cloud9 will report: "We are creating your AWS Cloud9 environment. This can take a few minutes."

![Cloud 9 - Name Environment](/img/cloud9_idx_6.png)

The Cloud9 instance will need some additional size for the Managed ELKK project. To increase the Amazon EBS volume to 50GB complete the following steps (additional details can be found at: https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html).

Create a new file in Cloud9:

![Cloud 9 - New fileame](/img/cloud9_idx_7.png)

Paste in the below content and save the file.

```sh
#!/bin/bash

# Specify the desired volume size in GiB as a command-line argument. If not specified, default to 20 GiB.
SIZE=${1:-20}

# Install the jq command-line JSON processor.
sudo yum -y install jq

# Get the ID of the envrionment host Amazon EC2 instance.
INSTANCEID=$(curl http://169.254.169.254/latest/meta-data//instance-id)

# Get the ID of the Amazon EBS volume associated with the instance.
VOLUMEID=$(aws ec2 describe-instances --instance-id $INSTANCEID | jq -r .Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId)

# Resize the EBS volume.
aws ec2 modify-volume --volume-id $VOLUMEID --size $SIZE

# Wait for the resize to finish.
while [ "$(aws ec2 describe-volumes-modifications --volume-id $VOLUMEID --filters Name=modification-state,Values="optimizing","completed" | jq '.VolumesModifications | length')" != "1" ]; do
  sleep 1
done

# Rewrite the partition table so that the partition takes up all the space that it can.
sudo growpart /dev/xvda 1

# Expand the size of the file system.
sudo resize2fs /dev/xvda1
```

![Cloud 9 - Save fileame](/img/cloud9_idx_8.png)

Save the file as "resize.sh".

![Cloud 9 - Save As](/img/cloud9_idx_9.png)

Execute the resize script with the command:

```bash
# run resize script
sh resize.sh 50
```

![Cloud 9 - Execute resize](/img/cloud9_idx_10.png)

The Cloud9 instance needs to be restarted for the resize to be effected.

Run the command below.

```bash
# execute instance restart
sudo reboot
```

![Cloud 9 - Reboot](/img/cloud9_idx_11.png)

Cloud9 will restart, wait a few minutes and then refresh the page.

![Cloud 9 - Wait](/img/cloud9_idx_12.png)
