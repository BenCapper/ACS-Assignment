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
systemctl start httpd"""
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


resource.create_instances(
    ImageId = "ami-0bf84c42e04519c85",
    KeyName = key_name,
    UserData = user_data,
    InstanceType = "t2.micro",
    SecurityGroupIds = grp_id,
    MinCount = 1,
    MaxCount = 1,
)
# Wait until finish
# SSH in and get metadata
# Configure index and scp image and text
# Print metadata

