import time
import os
import boto3
import requests
import datetime
import subprocess
import webbrowser
from boto3.dynamodb.conditions import Key


# Database item class
class db_item:
    def __init__(self, title, year, artist=None):
        self.title = title
        self.year = year
        self.artist = artist


# Database get item method
def get_item(table, title, year):
    try:
        item_response = table.get_item(Key={"title": title, "year": year})
        found_item = item_response["Item"]
        pretty_print(f"Found Item: {found_item}")
    except:
        pretty_print(f"Could not find the item: {title}")


# Core Functionality Methods
def sleep(duration):
    time.sleep(duration)


# Run subprocess commands wrapped in try/except
def subproc(cmd, pass_str, err_str, sleep_dur, output=None):
    sleep(sleep_dur)
    if output is True:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True)
            pretty_print(pass_str)
            return result
        except:
            pretty_print(err_str)
    else:
        try:
            subprocess.run(cmd, shell=True)
            pretty_print(pass_str)
        except:
            pretty_print(err_str)


# Work with files with print statements
def work_with_file(fname, opt, the_str, pass_str, err_str, sleep_dur):
    sleep(sleep_dur)
    try:
        with open(fname, opt) as file:
            file.write(the_str)
            file.close()
        pretty_print(pass_str)
    except:
        pretty_print(err_str)


# More legible output, log to a file
def pretty_print(the_string):
    print("------------------------------------------------------")
    print(the_string)
    print("------------------------------------------------------")
    with open("log.txt", "a") as logfile:
        logfile.write(str(datetime.datetime.now())[:-7] + ":  " + the_string + "\n")
        logfile.close()


# Global vars
# Boto3 requirements
region = "eu-west-1"
ec2_resource = boto3.resource("ec2")
ec2_client = boto3.client("ec2")
s3_resource = boto3.resource("s3")
s3_client = boto3.client("s3", region_name=region)
db_client = boto3.client("dynamodb")
db_resource = boto3.resource("dynamodb")

# Strings
key_file_name = "assign_one.pem"
sec_grp = "assignment_one"
table_name = "music"
image_name = "found_image.jpg"
log_name = "log.txt"
index_file = "index.html"
ami_resp = ""
key_name = ""
key_response = ""
public_ip = ""
bucket_name = ""
assign_one_key = ""
found_key_name = ""

# Lists
string_list = list()
grp_id = list()
key_name_list = ["assign_one"]

# Database objects
music = db_item("Test Title", 2022, "John")
music_two = db_item("Title ", 2020, "Item")

# Url
image_url = "https://witacsresources.s3-eu-west-1.amazonaws.com/image.jpg"

# Inst Tag
tag = {"Key": "Name", "Value": key_name_list[0]}

# Script
user_data = """
#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
systemctl start sshd.service
systemctl start ssh.service
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



# If old log exists
if os.path.exists(log_name):
    # Delete
    subproc(f"rm -f {log_name}", "Deleted old log file", "No old log file found", 1)



# Check if the assign_one keypair exists
try:
    sleep(1)
    found_key_name = ec2_client.describe_key_pairs(
        KeyNames=key_name_list
    )["KeyPairs"][0]["KeyName"]
except:
    found_key_name = ""
    pretty_print("Keypair assign_one does not exist")

# Delete any existing keypair named assign_one locally
if os.path.exists(key_file_name):
    subproc(
        f"rm -f {key_file_name}",
        "Deleted old keypair file locally",
        "Could not delete old local keypair",
        1,
    )
else:
    sleep(1)
    pretty_print("No old keypairs found")

# If there is already an AWS key named assign_one, delete it
if found_key_name == key_name_list[0]:
    try:
        delete_key_resp = ec2_client.delete_key_pair(
            KeyName=found_key_name
        )
        sleep(1)
        pretty_print("Deleted old keypair from AWS")
    except:
        pretty_print(f"Could not delete the AWS keypair: {found_key_name}")

# Keypair now deleted on both AWS and locally

# Create a new keypair on AWS
try:
    sleep(1)
    key_response = ec2_client.create_key_pair(
        KeyName=key_name_list[0],
        KeyType="rsa"
    )
    assign_one_key = key_response["KeyMaterial"]
    key_name = key_response["KeyName"]
    pretty_print(f"Keypair {key_file_name} created on AWS")
except:
    pretty_print(f"Keypair {key_file_name} could not be created on AWS")

# Save keypair data to file
work_with_file(
    key_file_name,
    "w",
    assign_one_key,
    f"Keypair {key_file_name} created locally",
    f"Keypair {key_file_name} could not be created locally",
    1,
)



try:
    # Check if security group already exists
    sleep(1)
    desc_response = ec2_client.describe_security_groups(
        GroupNames=[sec_grp]
        )
    grp_id.append(desc_response[
        "SecurityGroups"][0]["GroupId"]
        )
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



# Get image AMI by desc as ->
# aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2 --region eu-west-1 >> log.txt"""
# returns 2nd most recent ami?
try:
    ami_resp = ec2_client.describe_images(
        Filters=[
            {
                "Name": "description",
                "Values": [
                    "Amazon Linux 2 Kernel 5.10 AMI 2.0.20220218.1 x86_64 HVM gp2"
                ],
            }
        ]
    )["Images"][0]["ImageId"]
    pretty_print(f"Successfully retrieved image AMI: {ami_resp}")
except:
    pretty_print(f"Could not retrieve the image AMI")

# Create the instance
try:
    create_response = ec2_resource.create_instances(
        ImageId=ami_resp,
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



# Add a tag to the instance
try:
    created_instance.create_tags(Tags=[tag])
    pretty_print(f"Tag added to instance: {tag}")
except:
    pretty_print(f"Could not add tag to the instance: {tag}")



# Set keypair file permissions
subproc(
    f"chmod 400 {key_file_name}",
    "Keypair permissions set",
    "Could not set keypair permissions",
    2,
)

# ssh into instance and print public ip
ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_file_name} ec2-user@{public_ip} 'echo ; echo Public IPV4: {public_ip}'"
result = subproc(
    ssh_command,
    "Remote ssh echo completed",
    "Remote ssh echo failed",
    2,
    True
)

# First ssh attempt failed, keep trying
while result.returncode != 0:
    pretty_print("Failed ssh attempt, trying again...")
    result = subproc(
    ssh_command,
    "Remote ssh echo completed",
    "Remote ssh echo failed",
    2,
    True
)
pretty_print(str(result.stdout)[4:-3])



# Secure copy monitor script onto instance
subproc(
    f"scp -o StrictHostKeyChecking=no -i {key_file_name} monitor.sh ec2-user@{public_ip}:.",
    "Monitor script copied onto ec2 instance",
    "Monitor script was not copied onto ec2 instance",
    2,
)

# Set monitor permissions
subproc(
    f"ssh -o StrictHostKeyChecking=no -i {key_file_name} ec2-user@{public_ip} 'chmod 700 monitor.sh'",
    "Monitor script permissions set",
    "Monitor script permissions were not set",
    2,
)



# Delete old music db table
try:
    sleep(2)
    delete_table_resp = db_client.delete_table(
        TableName=table_name
    )
    pretty_print("Deleting an old table")
    waiter = db_client.get_waiter("table_not_exists")
    waiter.wait(TableName=table_name)
    pretty_print("Deleted old database table")
except:
    pretty_print("No previously made database table to delete")

# Create music database while web server loads
try:
    sleep(2)
    table_create_response = db_client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "year", "KeyType": "HASH"},  # Partition Key
            {"AttributeName": "title", "KeyType": "RANGE"},  # Sort Key
        ],
        AttributeDefinitions=[
            {"AttributeName": "year", "AttributeType": "N"},
            {"AttributeName": "title", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 100, "WriteCapacityUnits": 100},
    )
    pretty_print(f"Database table created: {table_name}")
except:
    pretty_print(f"Database table already exists: {table_name}")

# Get the table resource and load data
try:
    music_table = db_resource.Table("music")
    music_table.load()
    pretty_print("Waiting for the table...")
    music_table.wait_until_exists()
    pretty_print(f"Successfully loaded the {table_name} table")
except:
    pretty_print(f"Could not load the {table_name} table")

# Put an item in the music table
try:
    sleep(2)
    music_table.put_item(
        Item={"title": music.title, "year": music.year, "artist": music.artist}
    )
    pretty_print(f"Created item: {music.title}")
except:
    pretty_print(f"Could not create item: {music}")

# Get the item just created
sleep(2)
get_item(music_table, music.title, music.year)

# Update the item just created
try:
    sleep(2)
    music_table.update_item(
        Key={"title": music.title, "year": music.year},
        UpdateExpression="SET artist = :val",
        ExpressionAttributeValues={":val": "Ben"},
    )
    pretty_print(f"Updated {music.title} successfully")
except:
    pretty_print(f"Could not update the item: {music.title}")

# Show update result
sleep(2)
get_item(music_table, music.title, music.year)

# Delete the item
try:
    sleep(2)
    music_table.delete_item(
        Key={
            "title": music.title,
            "year": music.year,
        }
    )
    print(f"Deleted the item: {music.title}")
except:
    print(f"Could not delete the item: {music.title}")

# Create 5 items in a batch
with music_table.batch_writer() as batch:
    for i in range(5):
        try:
            sleep(1)
            batch.put_item(
                Item={
                    "title": music_two.title + str(i + 1),
                    "year": music_two.year + i,
                    "artist": music_two.artist + " " + str(i + 1),
                }
            )
            pretty_print(f"Created item: {music_two.title + str(i + 1)}")
        except:
            pretty_print("Could not add items to the batch")

# Find any item matching year = 2022
try:
    sleep(2)
    title_query_response = music_table.query(
        KeyConditionExpression=Key("year").eq(2022)
    )
    result = title_query_response["Items"]
    print(f"Query found the item: {result[0]}")
except:
    print(f"Could not find item")



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



# Get image for bucket
try:
    found_image = requests.get(image_url)
    pretty_print(f"Successfully retrieved image from {image_url}")
    sleep(1)
except:
    pretty_print(f"Could not retrieve image from {image_url}")
    found_image=""

# Put image in bucket
try:
    sleep(2)
    put_response = s3_client.put_object(
        Body=found_image.content,
        Bucket=bucket_name,
        Key=image_name,
        ACL="public-read",
    )
    pretty_print("Image put in the bucket")
except:
    pretty_print("Could not put the image in the bucket")



# Create index.html
index_cmd = f"""
touch {index_file} ; 
chmod 777 {index_file} ;
echo '<html>\n' > {index_file} ; 
echo '<img src="found_image.jpg"></img>\n' >> {index_file}
"""
subproc(index_cmd, f"{index_file} created", f"Could not create {index_file}", 2)

# If index.html was created, change permissions
if os.path.exists(index_file):
    subproc(
        f"chmod 400 {index_file}",
        f"{index_file} permissions set",
        f"Could not set {index_file} permissions",
        2,
    )

# Put index.html in the bucket
try:
    sleep(2)
    index_response = s3_client.put_object(
        Body=open(index_file, "rb"),
        Bucket=bucket_name,
        Key=index_file,
        ACL="public-read",
        ContentType="text/html",
    )
    pretty_print(f"{index_file} put in the bucket")
except:
    pretty_print(f"Could not put {index_file} in the bucket")

# Set static web hosting
try:
    website_configuration = {
        "ErrorDocument": {"Key": "error.html"},
        "IndexDocument": {"Suffix": "index.html"},
    }
    web_config = s3_client.put_bucket_website(
        Bucket=bucket_name, WebsiteConfiguration=website_configuration
    )
    pretty_print("Bucket website configuration set")
except:
    print("Bucket website configuration not set")



# Execute monitor script
permiss_cmd = f"""ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'echo ------------------------------------------------------;
echo Executing monitor.sh ; 
echo ------------------------------------------------------;
echo                            ; 
./monitor.sh'
"""
subproc(
    permiss_cmd, "Monitor.sh executed successfully", "Could not execute Monitor.sh", 2
)



# Open web brower tabs
try:
    time.sleep(2)
    webbrowser.open_new_tab(f"http://{public_ip}")
    webbrowser.open_new_tab(
        f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
    )
    webbrowser.open_new_tab(
        f"https://{region}.console.aws.amazon.com/dynamodbv2/home?region={region}#tables"
    )
    pretty_print("Browser opened")
except:
    pretty_print("Could not open the browser")



# Finished
pretty_print("Script Finished")
