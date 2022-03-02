import subprocess
import time
import os
import boto3
import requests
import webbrowser
from botocore.exceptions import ClientError
import datetime


def sleep(duration):
    time.sleep(duration)


def subproc(cmd):
    subprocess.run(cmd, shell=True)


def pretty_print(the_string):
    print("------------------------------------------------------")
    print(the_string)
    print("------------------------------------------------------")
    with open("log.txt", "a") as logfile:
        logfile.write(str(datetime.datetime.now())[:-7] + ":  " + the_string + "\n")
        logfile.close()


# Global vars
region = "eu-west-1"
ec2_resource = boto3.resource("ec2")
ec2_client = boto3.client("ec2")
s3_resource = boto3.resource("s3")
s3_client = boto3.client("s3", region_name=region)

key_file_name = "assign_one.pem"
sec_grp = "assignment_one"
key_name = ""
key_response = ""
public_ip = ""
bucket_name = ""
assign_one_key = ""
found_key_name = ""

string_list = list()
grp_id = list()
key_name_list = ["assign_one"]

image_url = "https://witacsresources.s3-eu-west-1.amazonaws.com/image.jpg"

user_data = """
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
curl https://witacsresources.s3-eu-west-1.amazonaws.com/image.jpg -o /var/www/html/image.jpg
chmod 777 /var/www/html/image.jpg
echo '<br>' >> index.html
echo '<img src="image.jpg"></img>' >> index.html
cp index.html /var/www/html/index.html"""

try:
    if os.path.exists("log.txt"):
        subproc("rm -f log.txt")
        pretty_print("Deleted old log file")
        sleep(1)
except:
    pretty_print("No old log file found")

try:
    subproc("touch log.txt")
    pretty_print("Created a new log file")
    sleep(1)
except:
    pretty_print("Could not create a new log file")

try:
    subproc("chmod 700 log.txt")
    pretty_print("Log permissions set")
    sleep(1)
except:
    pretty_print("Could not set log permissions")

# Get image for bucket
try:
    found_image = requests.get(image_url)
    pretty_print(f"Successfully retrieved image from {image_url}")
    sleep(1)
except:
    pretty_print(f"Could not retrieve image from {image_url}")

if os.path.exists("found_image.jpg"):
    try:
        sleep(1)
        subproc("rm -f found_image.jpg")
        pretty_print("Old image file deleted successfully")
    except:
        pretty_print("Could not delete the old image file")
else:
    sleep(1)
    pretty_print("No old image file found")

# Create image file locally
try:
    sleep(1)
    subproc("touch found_image.jpg")
    pretty_print("Image file created locally")
except:
    pretty_print("Could not create image file locally")

# If the image file was created locally
if os.path.exists("found_image.jpg"):
    try:
        sleep(1)
        subproc("chmod 777 found_image.jpg")
        pretty_print("Permissions set for found_image.jpg")
    except:
        pretty_print("Could not set found_image.jpg permissions")
    try:
        sleep(1)
        with open("found_image.jpg", "wb") as f:
            f.write(found_image.content)
            f.close()
        pretty_print("Image content saved to found_image.jpg")
    except:
        pretty_print("Could not save image content to found_image.jpg")

# Check if the assign_one keypair exists
try:
    sleep(1)
    found_key_name = ec2_client.describe_key_pairs(KeyNames=key_name_list)["KeyPairs"][
        0
    ]["KeyName"]
except:
    found_key_name = ""
    pretty_print("Keypair assign_one does not exist")

# Delete any existing keypair named assign_one locally
if os.path.exists(key_file_name):
    sleep(1)
    subproc(f"rm -f {key_file_name}")
    pretty_print("Deleted old keypair file locally")
else:
    sleep(1)
    pretty_print("No old keypairs found")

# If there is already an AWS key named assign_one, delete it
if found_key_name == key_name_list[0]:
    try:
        delete_key_resp = ec2_client.delete_key_pair(KeyName=found_key_name)
        sleep(1)
        pretty_print("Deleted old keypair from AWS")
    except:
        pretty_print(f"Could not delete the AWS keypair: {found_key_name}")

# Keypair now deleted on both AWS and locally

# Create a new keypair on AWS and save locally
try:
    sleep(1)
    key_response = ec2_client.create_key_pair(KeyName=key_name_list[0], KeyType="rsa")
    assign_one_key = key_response["KeyMaterial"]
    key_name = key_response["KeyName"]
    pretty_print(f"Keypair {key_file_name} created on AWS")
except:
    pretty_print(f"Keypair {key_file_name} could not be created on AWS")

try:
    sleep(1)
    subproc("touch assign_one.pem")
    subproc("chmod 777 assign_one.pem")
    with open(key_file_name, "w") as keyfile:
        keyfile.write(assign_one_key)
        keyfile.close()
    pretty_print(f"Keypair {key_file_name} created locally")
except:
    pretty_print(f"Keypair {key_file_name} could not be created locally")

try:
    # Check if security group already exists
    sleep(1)
    desc_response = ec2_client.describe_security_groups(GroupNames=[sec_grp])
    grp_id.append(desc_response["SecurityGroups"][0]["GroupId"])
except:
    pretty_print(f"Could not find the {sec_grp} security group")

# grp_id isnt empty, use that security group
if grp_id:
    sleep(1)
    pretty_print(f"Using the security group: {sec_grp}")
# grp_id is empty, create new security group
else:
    try:
        sleep(1)
        sec_grp_resp = ec2_resource.create_security_group(
            GroupName=sec_grp, Description="Assignment1"
        )
        pretty_print(f"Created the security group: {sec_grp}")
    except:
        pretty_print(f"Could not create the security group: {sec_grp}")
    # If the create function was successful, set ip permissions
    if sec_grp_resp:
        try:
            sleep(1)
            # Ref: https://stackoverflow.com/questions/66441122/how-to-access-my-instance-through-ssh-writing-boto3-code
            sec_ingress_response = sec_grp_resp.authorize_ingress(
                IpPermissions=[
                    {
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpProtocol": "tcp",
                        "IpRanges": [
                            {"CidrIp": "0.0.0.0/0", "Description": "internet"},
                        ],
                    },
                    {
                        "FromPort": 80,
                        "ToPort": 80,
                        "IpProtocol": "tcp",
                        "IpRanges": [
                            {"CidrIp": "0.0.0.0/0", "Description": "internet"},
                        ],
                    },
                ],
            )
            pretty_print(f"Security group rules set for: {sec_grp}")
        except:
            pretty_print("Security group rules not set")
        try:
            # Get the new security group id
            sleep(1)
            desc_security = ec2_client.describe_security_groups(GroupNames=[sec_grp])
            grp_id.append(desc_security["SecurityGroups"][0]["GroupId"])
            pretty_print(f"Using the security group: {sec_grp}")
        except:
            pretty_print(f"Could not create the security group: {sec_grp}")

try:
    create_response = ec2_resource.create_instances(
        ImageId="ami-0bf84c42e04519c85",
        KeyName=key_name,
        UserData=user_data,
        InstanceType="t2.nano",
        SecurityGroupIds=grp_id,
        MinCount=1,
        MaxCount=1,
    )
    pretty_print(f"Instance created")
    created_instance = create_response[0]
    created_instance.wait_until_running()
    pretty_print(f"Instance running")
    created_instance.reload()
    created_instance.wait_until_running()
    public_ip = created_instance.public_ip_address
except:
    pretty_print("Could not create ec2 instance")

try:
    sleep(2)
    subproc("chmod 400 assign_one.pem")
    pretty_print("Keypair permissions set")
except:
    pretty_print("Could not set keypair permissions")

try:
    sleep(2)
    ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_file_name} ec2-user@{public_ip} 'echo ; echo Public IPV4: {public_ip}'"
    subproc(ssh_command)
    pretty_print("Remote ssh echo completed")
except:
    pretty_print("Remote ssh echo failed")

try:
    sleep(2)
    subproc("chmod 777 monitor.sh")
    pretty_print("Monitor.sh permissions set, ready to copy to AWS")
except:
    pretty_print("Monitor.sh permissions not set, error may occur copying to AWS")

try:
    sleep(2)
    scp_cmd = f"scp -o StrictHostKeyChecking=no -i {key_file_name} monitor.sh ec2-user@{public_ip}:."
    subproc(scp_cmd)
    pretty_print("Monitor script copied onto ec2 instance")
except:
    pretty_print("Monitor script was not copied onto ec2 instance")

try:
    sleep(2)
    monitor_chmod_cmd = f"ssh -o StrictHostKeyChecking=no -i {key_file_name} ec2-user@{public_ip} 'chmod 700 monitor.sh'"
    subproc(monitor_chmod_cmd)
    pretty_print("Monitor script permissions set")
except:
    pretty_print("Monitor script permissions were not set")


# Use datetime to get unique bucket name
datetime_now = str(datetime.datetime.now())
string_list = datetime_now.split(" ")
datetime_now = string_list[0] + string_list[1]
string_list.clear()
string_list = datetime_now.split("-")
datetime_now = string_list[0] + string_list[1] + string_list[2]
string_list.clear()
string_list = datetime_now.split(":")
datetime_now = string_list[0] + string_list[1] + string_list[2]
string_list.clear()
string_list = datetime_now.split(".")
datetime_now = string_list[0] + string_list[1]
bucket_name = "bencapperwit" + datetime_now

# Create the bucket
location = {"LocationConstraint": region}
bucket_response = s3_client.create_bucket(
    Bucket=bucket_name, CreateBucketConfiguration=location, ACL="public-read"
)

# Wait for the bucket to exist
waiter = s3_client.get_waiter("bucket_exists")
waiter.wait(Bucket=bucket_name)
pretty_print(f"Bucket created named: {bucket_name}")

# Set image permissions
sleep(2)
open("found_image.jpg", "rb")
subprocess.run("chmod 400 found_image.jpg", shell=True)
pretty_print("Image permissions set")

# Put image in bucket
try:
    sleep(2)
    put_response = s3_client.put_object(
        Body=found_image.content,
        Bucket=bucket_name,
        Key="found_image.jpg",
        ACL="public-read",
    )
    pretty_print("Image put in the bucket")
except:
    pretty_print("Could not put the image in the bucket")


# Create index.html
try:
    sleep(2)
    index_cmd = """
touch index.html ; 
chmod 777 index.html ;
echo '<html>\n' > index.html ; 
echo '<img src="found_image.jpg"></img>\n' >> index.html
"""
    subproc(index_cmd)
    pretty_print("index.html created")
except:
    pretty_print("Could not create index.html")

# If index.html was created, change permissions
if os.path.exists("index.html"):
    try:
        sleep(2)
        subproc("chmod 400 index.html")
        pretty_print("index.html permissions set")
    except:
        pretty_print("Could not set index.html permissions")

# Put index.html in the bucket
try:
    sleep(2)
    index_response = s3_client.put_object(
        Body=open("index.html", "rb"),
        Bucket=bucket_name,
        Key="index.html",
        ACL="public-read",
        ContentType="text/html",
    )
    pretty_print("index.html put in the bucket")
except:
    pretty_print("Could not put index.html in the bucket")

try:
    website_configuration = {
        "ErrorDocument": {"Key": "error.html"},
        "IndexDocument": {"Suffix": "index.html"},
    }
    web_config = s3_client.put_bucket_website(
        Bucket=bucket_name, WebsiteConfiguration=website_configuration
    )
    print("Bucket website configuration set")
except:
    print("index.html not created")

# Set permissions for monitor script
try:
    sleep(2)
    permiss_cmd = f"""ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'chmod 700 monitor.sh ; 
        echo ------------------------------------------------------; 
        echo Monitor.sh permissions set ; 
        echo ------------------------------------------------------;
        echo                            ; 
        echo ------------------------------------------------------;
        echo Executing monitor.sh ; 
        echo ------------------------------------------------------;
        echo                            ; 
        ./monitor.sh'
        """
    subproc(permiss_cmd)
    time.sleep(12)
    webbrowser.open_new_tab(f"http://{public_ip}")
    webbrowser.open_new_tab(
        f"https://{bucket_name}.s3.{region}.amazonaws.com/index.html"
    )
    pretty_print("Browser opened")
except:
    pretty_print("Could not open the browser")
