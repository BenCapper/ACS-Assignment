import subprocess
import time
import os
import boto3
import requests
import webbrowser
from botocore.exceptions import ClientError
import datetime


def subproc(cmd):
    subprocess.run(cmd, shell=True)

def pretty_print(the_string):
    print("------------------------------------------------------")
    print(the_string)
    print("------------------------------------------------------")

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


# Get image for bucket
try:
    found_image = requests.get(image_url)
    subproc("chmod 777 found_image.jpg")
    with open("found_image.jpg", "wb") as f:
        f.write(found_image.content)
        f.close()
    pretty_print(f"Successfully retrieved image from {image_url}")
except:
    pretty_print(f"Failed to retrieve image from {image_url}")

# Check if the assign_one keypair exists
try:
    found_key_name = ec2_client.describe_key_pairs(
        KeyNames=key_name_list)["KeyPairs"
        ][0]["KeyName"]
except:
    found_key_name = ""
    pretty_print("Keypair assign_one does not exist")

# Delete any existing keypair named assign_one locally
if os.path.exists(key_file_name):
    subproc(f"rm -f {key_file_name}")
    pretty_print("Deleted old keypair file locally")
else:
    pretty_print("No old keypairs found")

# If there is already an AWS key named assign_one, delete it
if found_key_name == key_name_list[0]:
    try:
        delete_key_resp = ec2_client.delete_key_pair(
            KeyName = found_key_name
        )
        time.sleep(5)
        pretty_print("Deleted old keypair from AWS")
    except:
        pretty_print(f"Could not delete the AWS keypair: {found_key_name}")

# Keypair now deleted on both AWS and locally

# Create a new keypair on AWS and save locally
try:
    key_response = ec2_client.create_key_pair(KeyName=key_name_list[0], KeyType="rsa")
    assign_one_key = key_response["KeyMaterial"]
    key_name = key_response["KeyName"]
    pretty_print(f"Keypair {key_file_name} created on AWS")
except:
    pretty_print(f"Keypair {key_file_name} could not be created on AWS")

try:
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
    desc_response = ec2_client.describe_security_groups(GroupNames=[sec_grp])
    grp_id.append(desc_response["SecurityGroups"][0]["GroupId"])
except:
    pretty_print(f"Could not find the {sec_grp} security group")

# grp_id isnt empty, use that security group
if grp_id:
    pretty_print(f"Using the security group: {sec_grp}")
# grp_id is empty, create new security group
else:
    try:
        sec_grp_resp = ec2_resource.create_security_group(GroupName=sec_grp, Description="Assignment1")
        pretty_print(f"Created the security group: {sec_grp}")
    except:
        pretty_print(f"Could not create the security group: {sec_grp}")
    # If the create function was successful, set ip permissions
    if sec_grp_resp:
        try:
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
    subproc("chmod 400 assign_one.pem")
    subprocess.run("chmod 400 assign_one.pem", shell=True)
    pretty_print("Keypair permissions set")
except:
    pretty_print("Could not set keypair permissions")

try:
    ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'echo ; echo Public IPV4: {public_ip}'"
    subproc(ssh_command)
    pretty_print("Remote ssh echo completed")
except:
    pretty_print("Remote ssh echo failed")

try:
    monitor_chmod_cmd = f"ssh -i {key_name}.pem ec2user@{public_ip} 'chmod 700 monitor.sh'"
    subproc(monitor_chmod_cmd)
    pretty_print("Monitor script permissions set")
except:
    pretty_print("Monitor script permissions were not set")

try:
    scp_cmd = f"scp -i {key_name}.pem monitor.sh ec2-user@{public_ip}:."
    subproc(scp_cmd)
    pretty_print("Monitor script copied onto ec2 instance")
except:
    pretty_print("Monitor script was not copied onto ec2 instance")

---------------------------------------------------------------------------------------------------------

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
print(f"""
---------------------------
Bucket created named: {bucket_name}
---------------------------""")

# Set image permissions and put in bucket
open("found_image.jpg", "rb")
subprocess.run("chmod 400 found_image.jpg", shell=True)
print("""
---------------------------
Image permissions set
---------------------------""")
put_response = s3_client.put_object(
    Body=found_image.content,
    Bucket=bucket_name,
    Key="found_image.jpg",
    ACL="public-read",
)
print("""
---------------------------
Image put in the bucket
---------------------------
    """)

# Create index.html, set permissions, put in bucket
try:
    index_cmd = """
    touch index.html ; 
    chmod 777 index.html ;
    echo '<html>\n' > index.html ; 
    echo '<img src="found_image.jpg"></img>\n' >> index.html
    """
    subproc(index_cmd)
    #subprocess.run(index_cmd, shell=True)
    print("""
---------------------------
index.html created
---------------------------""")
    subproc("chmod 400 index.html")
    #subprocess.run("chmod 400 index.html", shell=True)
    print("""
---------------------------
index.html permissions set
---------------------------""")
    index_response = s3_client.put_object(
        Body=open("index.html", "rb"),
        Bucket=bucket_name,
        Key="index.html",
        ACL="public-read",
        ContentType="text/html",
    )
    print("""
---------------------------
index.html put in the bucket
---------------------------""")
    website_configuration = {
        "ErrorDocument": {"Key": "error.html"},
        "IndexDocument": {"Suffix": "index.html"},
    }
    web_config = s3_client.put_bucket_website(
        Bucket=bucket_name, WebsiteConfiguration=website_configuration
    )
    print("""
---------------------------
Bucket website configuration set
---------------------------""")
except:
    print("index.html not created")

# Set permissions for monitor script
try:
    time.sleep(5)
    permiss_cmd = f"""ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'chmod 700 monitor.sh ; 
        echo ---------------------------; 
        echo Monitor.sh permissions set ; 
        echo ---------------------------;
        echo                            ; 
        echo ---------------------------;
        echo Executing monitor.sh ; 
        echo ---------------------------;
        echo                            ; 
        ./monitor.sh'
        """
    subproc(permiss_cmd)
    #subprocess.run(permiss_cmd, shell=True)
    time.sleep(40)
    webbrowser.open_new_tab(f"http://{public_ip}")
    webbrowser.open_new_tab(
        f"https://{bucket_name}.s3.{region}.amazonaws.com/index.html"
    )
    print("""
---------------------------
Browser opened
---------------------------""")
except:
    print("Couldn't open the browser")


