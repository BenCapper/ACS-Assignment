import subprocess
import os
import time
import boto3
import requests
import webbrowser
from botocore.exceptions import ClientError
from tomlkit import datetime


resource = boto3.resource("ec2")
client = boto3.client("ec2")
s3_resource = boto3.resource("s3")
s3_client = boto3.client("s3")

key_name = ""
key_response = ""
key_name_list = ["assign_one"]


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

try:
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
            f.close()
        print("Keypair file created")
    else:
        key_response = client.describe_key_pairs(KeyNames=key_name_list)["KeyPairs"][0]
        key_name = key_response["KeyName"]
        key_id = key_response["KeyPairId"]
        print("Using previously created keypair")
except:
    print("Error creating keypair")


# Save key to file
# Change permissions on file
try:
    # Check if security group already exists
    response = client.describe_security_groups(GroupNames=["ssh-http"])
    grp_id = list()
    grp_id.append(response["SecurityGroups"][0]["GroupId"])
    ("Using the ssh-http security group")
except ClientError as e:
    print("Couldnt find the ssh-http security group")

public_ip = ""

try:
    create_response = resource.create_instances(
    ImageId = "ami-0bf84c42e04519c85",
    KeyName = key_name,
    UserData = user_data,
    InstanceType = "t2.micro",
    SecurityGroupIds = grp_id,
    MinCount = 1,
    MaxCount = 1,
    )
    print("Instance created")
    created_instance = create_response[0]
    created_instance.wait_until_running()
    print("Instance running")
    time.sleep(20)
    created_instance.reload()
    created_instance.wait_until_running()
    public_ip = created_instance.public_ip_address
    subprocess.run("chmod 400 assign_one.pem", shell=True)
    print("Keypair permissions set")
    ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'echo Public IPV4: {public_ip}'"
    subprocess.run(ssh_command, shell=True)
    print("Remote ssh echo completed")
except:
    print("ec2 creation failed")

# SSH in and get metadata
# Configure index and scp image and text
# Print metadata

bucket_name = ""

try:
    date_now = datetime.date
    time_now = datetime.time
    bucket_name = public_ip+"-"+f"{date_now}-{time_now}"
    bucket_response = s3_resource.create_bucket(Bucket = bucket_name)
    print(bucket_response)
    print(f"Bucket created with name: {bucket_name}")
except:
    print("Bucket couldn't be created")


try:
    found_image = requests.get("https://witacsresources.s3-eu-west-1.amazonaws.com/image.jpg")
    with open('found_image.jpg', 'wb') as f:
        f.write(found_image.content)
        f.close()
    subprocess.run("chmod 644 found_image.jpg", shell=True)
    print("Image permissions set")
    put_response = s3_resource.Object(bucket_name, found_image).put(Body = open(found_image, "rb"))
    print(put_response)
    print("Image put in the bucket successfully")
except:
    print("Couldn't put the file in the bucket")

try:
    index_cmd = """
    touch index.html ; 
    echo '<html>\n' > index.html ; 
    echo '<img src="found_image.jpg"></img>\n' >> index.html
    """
    subprocess.run(index_cmd, shell=True)
    print("index.html created")
    subprocess.run("chmod 400 index.html", shell=True)
    print("index.html permissions set")
    index_response = s3_resource.Object(bucket_name, "index.html").put(Body = open("index.html", "rb"))
    print("index.html put in the bucket successfully")
    web_config = s3_client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration = "website_configuration")
    print("Bucket website configuration set")
except:
    print("index.html not created")

try:
    webbrowser.open_new_tab(f"http://{public_ip}")
    webbrowser.open_new_tab()
    print("Browser opened")
except:
    print("Couldn't open the browser")