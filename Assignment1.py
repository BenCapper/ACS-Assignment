from re import T
import subprocess
import time
import boto3
import requests
import webbrowser
from botocore.exceptions import ClientError
import datetime


# Setup global variables
region = "eu-west-1"
resource = boto3.resource("ec2")
client = boto3.client("ec2")
s3_resource = boto3.resource("s3")
s3_client = boto3.client("s3", region_name=region)
key_name = ""
key_response = ""
key_name_list = ["assign_one"]
public_ip = ""
bucket_name = ""
string_list = list()
found_image = requests.get(
    "https://witacsresources.s3-eu-west-1.amazonaws.com/image.jpg"
)
subprocess.run("chmod 777 found_image.jpg", shell=True)
with open("found_image.jpg", "wb") as f:
    f.write(found_image.content)
    f.close()

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

# Check if the keypair already exists
try:
    found_key_name = client.describe_key_pairs(
        KeyNames=key_name_list)["KeyPairs"
        ][0]["KeyName"]
except:
    found_key_name = ""

# If the found key isnt "assign-one"
try:
    if key_name_list[0] != found_key_name:
        key_response = client.create_key_pair(KeyName="assign_one", KeyType="rsa")
        assign_one_key = key_response["KeyMaterial"]
        key_name = key_response["KeyName"]
        key_id = key_response["KeyPairId"]
        with open("assign_one.pem", "w") as f:
            f.write(assign_one_key)
            f.close()
        print("""
---------------------------
Keypair file created
---------------------------""")
# If the found key is "assign-one", get its values
    else:
        key_response = client.describe_key_pairs(KeyNames=key_name_list)["KeyPairs"][0]
        key_name = key_response["KeyName"]
        key_id = key_response["KeyPairId"]
        print(f"""
---------------------------
Using keypair: {key_name}
---------------------------""")
except:
    print("Error creating keypair")


try:
    # Check if security group already exists
    response = client.describe_security_groups(GroupNames=["ssh-http"])
    grp_id = list()
    grp_id.append(response["SecurityGroups"][0]["GroupId"])
    print("""
---------------------------
Using the ssh-http security group
---------------------------""")
except ClientError as e:
    print("Couldnt find the ssh-http security group")

# Create the instance
try:
    create_response = resource.create_instances(
        ImageId="ami-0bf84c42e04519c85",
        KeyName=key_name,
        UserData=user_data,
        InstanceType="t2.micro",
        SecurityGroupIds=grp_id,
        MinCount=1,
        MaxCount=1,
    )
    print("""
---------------------------
Instance created
---------------------------""")
    created_instance = create_response[0]
    created_instance.wait_until_running()
    print("""
---------------------------
Instance running
---------------------------""")
    # Reload and wait for instance
    created_instance.reload()
    created_instance.wait_until_running()
    public_ip = created_instance.public_ip_address
    subprocess.run("chmod 400 assign_one.pem", shell=True)
    print("""
---------------------------
Keypair permissions set
---------------------------""")
    time.sleep(10)
    ssh_command = f"ssh -o StrictHostKeyChecking=no -i {key_name}.pem ec2-user@{public_ip} 'echo ; echo Public IPV4: {public_ip}'"
    subprocess.run(ssh_command, shell=True)
    print("""
---------------------------
Remote ssh echo completed
---------------------------""")
    # Secure copy monitor script onto instance
    scp_cmd = f"scp -i {key_name}.pem monitor.sh ec2-user@{public_ip}:."
    subprocess.run(scp_cmd, shell=True)
    print("""
---------------------------
Monitor script copied
---------------------------""")

except:
    print("ec2 creation failed")

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
    subprocess.run(index_cmd, shell=True)
    print("""
---------------------------
index.html created
---------------------------""")
    subprocess.run("chmod 400 index.html", shell=True)
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
    subprocess.run(permiss_cmd, shell=True)
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
