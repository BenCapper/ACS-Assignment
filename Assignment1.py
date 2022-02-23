import subprocess
import os
import time
import boto3
import requests
from botocore.exceptions import ClientError

resource = boto3.resource("ec2")
client = boto3.client("ec2")

key_name = ""
key_response = ""
key_name_list = ["assign_one"]

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
echo '<br>' >> index.html
echo 'Availability Zone: ' >> index.html
curl http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html
echo '<br>' >> index.html
echo 'Subnet: ' >> index.html
MAC=$(curl http://169.254.169.254/latest/meta-data/mac)
curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/${MAC}/subnet-id >> index.html
cp index.html /var/www/html/index.html"""
)

try:
    found_key_name = client.describe_key_pairs(KeyNames=key_name_list)["KeyPairs"][0]["KeyName"]
except:
    found_key_name = ""    

if key_name_list[0] != found_key_name:
    key_response = client.create_key_pair(
        KeyName = 'assign_one',
        KeyType = 'rsa'
    )
    assign_one_key = key_response["KeyMaterial"]
    key_name = key_response["KeyName"]
    key_id = key_response["KeyPairId"]
    with open('assign_one.pem', 'w') as f:
        f.write(assign_one_key)
else:
    key_response = client.describe_key_pairs(KeyNames=key_name_list)["KeyPairs"][0]
    key_name = key_response["KeyName"]
    key_id = key_response["KeyPairId"]


# Save key to file
# Change permissions on file
try:
    # Check if security group already exists
    response = client.describe_security_groups(GroupNames=["ssh-http"])
    grp_id = list()
    grp_id.append(response["SecurityGroups"][0]["GroupId"])
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


created_instance = create_response[0]
created_instance.wait_until_running()
print("Instance Running")
time.sleep(20)
created_instance.reload()
created_instance.wait_until_running()
public_ip = created_instance.public_ip_address
subprocess.run("chmod 400 assign_one.pem", shell=True)
ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'echo Public IPV4: {public_ip}'"
subprocess.run(ssh_command, shell=True)

# SSH in and get metadata
# Configure index and scp image and text
# Print metadata

