from asyncio import subprocess
import os
import boto3
from botocore.exceptions import ClientError

resource = boto3.resource("ec2")
client = boto3.client("ec2")

# response = client.describe_images(Filters=[{'Name': 'image-id', 'Values': ['ami-0bf84*']}])
# print(response)

user_data = (
    "#!/bin/bash \nyum -y install httpd \nsystemctl enable httpd \nservice httpd start"
)

try:
    response = client.describe_security_groups(GroupNames=["Assignment"])
    grp_id = list()
    grp_id.append(response["SecurityGroups"][0]["GroupId"])
    print(id)
except ClientError as e:
    print(e)

resource.create_instances(
    ImageId="ami-0bf84c42e04519c85",
    KeyName = "benkey",
    UserData=user_data,
    InstanceType="t2.micro",
    SecurityGroupIds=grp_id,
    MinCount=1,
    MaxCount=1,
)

