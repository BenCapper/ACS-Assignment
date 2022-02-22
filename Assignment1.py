from asyncio import subprocess
import os
import boto3
from botocore.exceptions import ClientError

resource = boto3.resource("ec2")
client = boto3.client("ec2")


# response = client.describe_images(Filters=[{'Name': 'image-id', 'Values': ['ami-0bf84*']}])
# print(response)

user_data = (
    """
#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
echo '<html>' > index.html
echo 'Private IP address: ' >> index.html
curl http://169.254.169.254/latest/meta-data/local-ipv4 >> index.html
cp index.html /var/www/html/index.html"""
)


# Check if the keypair already exists
key_response = client.create_key_pair(
    KeyName = 'assign_one',
    KeyType = 'rsa'
)
assign_one_key = key_response["KeyMaterial"]
key_name = key_response["KeyName"]
key_id = key_response["KeyPairId"]
# Save key to file
# Change permissions on file


try:
    # Check if security group already exists
    response = client.describe_security_groups(GroupNames=["Assignment"])
    grp_id = list()
    grp_id.append(response["SecurityGroups"][0]["GroupId"])
    print(id)
except ClientError as e:
    print(e)


create_response = resource.create_instances(
    ImageId = "ami-0bf84c42e04519c85",
    KeyName = key_name,
    UserData = user_data,
    InstanceType = "t2.micro",
    SecurityGroupIds = grp_id,
    MinCount = 1,
    MaxCount = 1,
)

# Check response for the instance id
print(create_response)
create_response.wait_until_running()
print("Instance Running")
create_response.reload()
# Get the instance IP address
ip_addr = 0
ssh_command = "ssh -o StrictHostKeyChecking=no -i ${key_name}.pem ec2-user@${ip_addr}"
subprocess.run(ssh_command, shell=True)
# Wait until finish
# SSH in and get metadata
# Configure index and scp image and text
# Print metadata

