#!/usr/bin/env python3
import boto3, json, random, string, subprocess, datetime, time, socket

# Initialize EC2 and S3 resources using boto3
ec2 = boto3.resource('ec2')
s3 = boto3.resource('s3')
s3client = boto3.client('s3')
snsClient = boto3.client('sns')

# Define constants
key_name = 'EvaUnit00'
security_group = 'sg-0d2f8f0a77bd98152'
image_url = 'http://devops.witdemo.net/logo.jpg'

print('!!! START OF SCRIPT !!!\n!!! Creating log file...')
# Creates a log file to store logs, https://www.pythontutorial.net/python-basics/python-write-text-file/
try: 
    with open('logs.txt','w') as file:
        file.write('//////////////////// START OF LOGS ////////////////////\n')
except Exception as error:
    print(f'Error while creating log file: {error}')

print('!!! Defining error logging method...')
# Defines a method to log messages to the log file
def log_to_logs(log):
    try:
        with open('logs.txt', 'a') as file:
            # Log the current timestamp and the log message, https://www.w3schools.com/python/python_datetime.asp
            file.write(f'{datetime.datetime.now()} : {log}\n')
    except Exception as error:
        print(f'Error writing to log file: {error}')

print('!!! Terminating previous instances (if any)...')
# Iterates through all EC2 instances and terminates any running ones
for instance in ec2.instances.all():
    if instance.state['Name'] == 'running':
        try:
            response = instance.terminate()
            log_to_logs(f"Instance termination response: {response}") # Logs the response from the termination
        except Exception as error:
            print (f'Error while terminating previous instances: {error}')

print('!!! Emptying previous buckets (if any)...')
# Iterates through all S3 buckets and deletes their contents
for bucket in s3.buckets.all():
    for key in bucket.objects.all():
        try:
            response = key.delete()
            log_to_logs(f"Empying bucket reponse: {response}") # Logs the response for each deleted key
        except Exception as error:
            print (f'Error while emptying previous buckets: {error}')

print('!!! Deleteing previous buckets (if any)...')
# Iterates through all S3 buckets and deletes them
for bucket in s3.buckets.all():
    try:
        response = bucket.delete()
        log_to_logs(f"Bucket deletion response: {response}") # Logs the response for each deleted bucket
    except Exception as error:
        print (f'Error while deleting previous buckets: {error}')

print('!!! Preparing new EC2 instance...')
# Creates a new EC2 instance with the specified parameters
try:
    new_instances = ec2.create_instances(
    ImageId='ami-0ebfd941bbafe70c6', # AMI ID
    MinCount=1, # Minimum number of instances to launch
    MaxCount=1, # Maximum number of instances to launch
    InstanceType='t2.nano', # Instance type
    KeyName=key_name, # Key pair
    SecurityGroupIds=[security_group], # Security Group
    UserData=f"""#!/bin/bash
                yum install httpd -y
                systemctl start httpd
                systemctl enable httpd
                TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`

                echo '<html>' > index.html

                echo '<p>Instance ID: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id >> index.html

                echo '<p>Private IP address: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4 >> index.html

                echo '<p>Instance Type: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type >> index.html

                echo '<p>Availability Zone: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html

                echo '<p>Security Group: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/security-groups >> index.html

                echo '<p>AMI ID: </p>' >> index.html
                curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/ami-id >> index.html

                cp index.html /var/www/html/index.html""") # Code to run once the instance starts
    log_to_logs(f"Instance creating response: {response}") # Logs the response for the new instance creation
except Exception as error:
    print(f'Error creating EC2 instance: {error}\n!!! Stopping script...')
    exit()

print('!!! Preparing new EC2 instance\'s tags...')
# Tags the newly created instance
try:
    response = new_instances[0].create_tags(
        Tags=[
            {
                'Key': 'Name', # Tag key
                'Value': 'EvaUnit01' # Tag value
            },
        ]
    )
    log_to_logs(f"Instance tagging response: {response}") # Logs the response for tagging
except Exception as error:
    print(f'Error while creating new instance\'s tags: {error}')

# Waits until the instance is fully created
new_instances[0].wait_until_exists()
print (f'!!! Instance {new_instances[0].id} created successfully!\n!!! Waiting for instance to run...')
new_instances[0].wait_until_running() # Waits until the instance is in the running state
print (f'!!! Instance {new_instances[0].id} is running! Visit the web page at: http://{new_instances[0].public_ip_address}\n!!! Writing website to freilly-websites.txt...')

# Writes the EC2 website to the websites.txt file
try: 
    with open('freilly-websites.txt','w') as file:
        response = file.write(f'EC2 Instance: http://{new_instances[0].public_ip_address}')
    log_to_logs(f"Writing to websites file response: {response}") # Logs the response of writing the file     
except Exception as error:
    print(f'Error writing to website file: {error}')

print('!!! Creating S3 bucket...')
# Generates a random bucket name and creates a new S3 bucket, https://stackoverflow.com/questions/2030053/how-to-generate-random-strings-in-python
try:
    new_bucket = s3.create_bucket(Bucket=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))+'-freilly')
    log_to_logs(f"S3 bucket creation response: {response}") # Logs the response for the bucket's creation
except Exception as error:
    print(f'Error creating S3 bucket: {error}\n!!! Stopping script...')
    exit()

print(f'!!! Configuring {new_bucket.name} website...')
# Configures the S3 bucket as a static website
website_configuration = {
 'ErrorDocument': {'Key': 'error.html'}, # Specify error document
 'IndexDocument': {'Suffix': 'index.html'}, # Specify index document
}

# Applies the website configuration to the newly created bucket
try:
    response = s3.BucketWebsite(new_bucket.name).put(WebsiteConfiguration=website_configuration)
    log_to_logs(f"Website configuration application to bucket response: {response}") # Logs the response for website configuration
except Exception as error:
    print(f'Error putting website configuration into S3 bucket: {error}\n!!! Stopping script...')
    exit()

# Deletes public access block to allow public access to the website
try:
    response = s3client.delete_public_access_block(Bucket=new_bucket.name)
    log_to_logs(f"Public access block deletion response: {response}") # Logs the response for remocing the public access block
except Exception as error:
    print(f'Error deleting public access block for S3 bucket: {error}')

# Defines the bucket policy to allow public read access
bucket_policy = {
    "Version": "2012-10-17",
    "Statement": 
    [
        {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*", # Allows access to everyone
         "Action": ["s3:GetObject"],
         "Resource": f"arn:aws:s3:::{new_bucket.name}/*"
         }
    ]
}

# Applies the bucket policy to the new S3 bucket
try:
    response = s3.Bucket(new_bucket.name).Policy().put(Policy=json.dumps(bucket_policy))
    log_to_logs(f"Bucket policy application response: {response}") # Logs the response for applying the bucket policy
except Exception as error:
    print(f'Error putting new policy into S3 bucket: {error}')


print('!!! Creating SNS topic to send an email whenever an object is created in bucket...')
# Creates an SNS topic
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/put_bucket_notification_configuration.html, 
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns/client/subscribe.html, 
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns/client/set_topic_attributes.html,
# https://docs.aws.amazon.com/code-library/latest/ug/python_3_sns_code_examples.html

try:
    response = snsClient.create_topic(Name='s3-notification-topic')
    topicArn = response['TopicArn'] # Retrieves the ARN of the created topic (Amazon Resource Name)
    log_to_logs(f"SNS topic creation response: {response}")
except Exception as error:
    print(f'Error creating new SNS topic: {error}')

# Subscribes specified email to the SNS topic for notifications
try:
    response = snsClient.subscribe(
        TopicArn=topicArn,
        Protocol='email',
        Endpoint='20101977@mail.wit.ie'
    )
    log_to_logs(f"Email subscription to SNS response: {response}")
except Exception as error:
    print(f'Error subscribing email to SNS topic: {error}')

# Defines a policy for the SNS topic, allowing S3 to publish messages to it
sns_topic_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect":"Allow",
            "Principal":{"Service": "s3.amazonaws.com"},
            "Action":"SNS:Publish",
            "Resource": topicArn,
            "Condition": {
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:s3:::{new_bucket.name}"
                }
            }
        }
    ]
}

# Sets the defined policy for the SNS topic
try:
    response = snsClient.set_topic_attributes(
        TopicArn=topicArn,
        AttributeName='Policy',
        AttributeValue=json.dumps(sns_topic_policy)
    )
    log_to_logs(f"SNS topic policy update response: {response}")
except Exception as error:
    print(f'Error setting SNS topic policy: {error}')

# Configures the S3 bucket to send notifications to the SNS topic for object creation events
try:
    response = s3client.put_bucket_notification_configuration(
        Bucket=new_bucket.name,
        NotificationConfiguration={
            'TopicConfigurations': [
                {
                    'Events': [
                        's3:ObjectCreated:*',
                    ],
                    'TopicArn': topicArn,
                },
            ],
        },
    )
    log_to_logs(f"Putting bucket notification configuration response: {response}")
except Exception as error:
    print(f'Error putting S3 bucket notification configuration: {error}')

print(f'!!! Downloading image from {image_url}...')
# Downloads an image from the specified URL
try:
    response = subprocess.run(['curl','-O', image_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(f"Image download response: {response}") # Logs the response from the image download
except Exception as error:
    print (f'Error downloading image from {image_url}: {error}')

print(f'!!! Uploading image from {image_url} to {new_bucket.name}...')
# Uploads the downloaded image to the S3 bucket
try:
    response = s3.Object(new_bucket.name,'logo.jpg').put(Body=open('logo.jpg','rb'),ContentType='image/jpeg')
    log_to_logs(f"Image upload to bucket response: {response}") # Log the response for the image upload
except Exception as error:
    print (f'Error uploading image from {image_url} to {new_bucket.name}: {error}')

print("!!! Creating index.html...")
# Creates an index.html file for the S3 bucket's website, https://www.geeksforgeeks.org/creating-and-viewing-html-files-with-python/
try:
    with open('index.html','w') as file:
        response = file.write(f"""<html>
    <head>
        <title>{new_bucket.name}'s Website!</title>
    </head>
    <body>
        <h2>Here is the image from {image_url}!</h2>
        <img src="http://{new_bucket.name}.s3.amazonaws.com/logo.jpg" alt="Looks like it didn't work LOL!">
        <p>Isn't it great! :D</p>
    </body>
</html>""")
        log_to_logs(f"Index.html creation response: {response}") # Logs the response for the index.html file creation
except Exception as error:
    print(f'Error creating index.html file: {error}')
    
print(f'!!! Uploading index.html to {new_bucket.name}...')
# Uploads the index.html file to the S3 bucket
try:
    response = s3.Object(new_bucket.name,'index.html').put(Body=open('index.html','rb'),ContentType='text/html')
    log_to_logs(f"Index.html upload response: {response}") # Logs the response for the index.html upload
except Exception as error:
 print (f'Error uploading index.html to {new_bucket.name}: {error}')

print(f'!!! {new_bucket.name} launched! Visit the web page at: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com\n!!! Writing website to freilly-websites.txt...')

try:
    with open('freilly-websites.txt','a') as file:
        response = file.write(f'\nS3 Bucket: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com')
    log_to_logs(f"Writing to website file response: {response}") # Logs the response for writing the website's URL
except Exception as error:
    print(f'Error writing to website file: {error}')

print(f'!!! Ensuring {key_name}.pem has correct permissions...')
# Ensures the correct permissions are set for the private key
try:
    command = f"chmod 400 {key_name}.pem" # Sets permissions for the key
    #https://stackoverflow.com/questions/11269575/how-to-hide-output-of-subprocess
    response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(f"Ensuring key permissions response: {response}") # Logs the response for the key's permissions change
except Exception as error:
    print(f'Error ensuring {key_name}.pem has correct permissions: {error}')

print(f'!!! Ensuring SSH to {new_instances[0].public_ip_address} is available...')
# https://stackoverflow.com/questions/47423746/how-can-i-verify-that-an-ssh-connection-is-possible-without-login-information, 
# https://docs.python.org/3/library/socket.html

def check_ssh(ip, port=22):
    # Checks if SSH is avaiable on the specified address and port (22 for SSH)
    try: 
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = test_socket.connect_ex((ip, 22))
        log_to_logs(f"Ensuring SSH to {new_instances[0].public_ip_address} is available response: {response}")
        test_socket.close()
        return response == 0 # If the response is 0, SSH is available
    except Exception as error:
        print(f'Error ensuring SSH to {new_instances[0].public_ip_address} is available: {error}')
        return False

# Checks for SSH access until it's available
while not check_ssh(new_instances[0].public_ip_address):
    print(f'!!! Waiting for SSH access to {new_instances[0].public_ip_address}...')
    time.sleep(2)

print(f'!!! SSH access available to {new_instances[0].public_ip_address}!\n!!! Copying monitoring.sh to {new_instances[0].public_ip_address}...')
# Copies the monitoring.sh script to the new EC2 instance
try:
    command = f"scp -o StrictHostKeyChecking=no -i {key_name}.pem monitoring.sh ec2-user@{new_instances[0].public_ip_address}:."
    response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(f"Monitoring.sh copying response: {response}") # Logs the response for the file copy
except Exception as error:
    print (f'Error copying monitoring.sh to {new_instances[0].public_ip_address}: {error}')

print('!!! Making monitoring.sh executable...')
# Changes the permissions of the monitoring.sh script to make it executable
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} 'chmod 700 monitoring.sh'"
    response = subprocess.run(command,shell=True)
    log_to_logs(f"Making monitoring.sh executable response: {response}") # Logs the response for permission change
except Exception as error:
    print (f'Error making monitoring.sh executable: {error}\n!!! Stopping script...')
    exit()

print('!!! Waiting for EC2 web service to run...')
# Waits until the HTTPD web service is running, https://www.tecmint.com/check-apache-httpd-status-and-uptime-in-linux/
while True:
    try:
       command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} 'systemctl is-active httpd'"
       response = subprocess.run(command, shell=True, capture_output=True, text=True)
       log_to_logs(f"Waiting for EC2 web service response: {response}") # Logs the response for checking service status
       if "inactive" not in response.stdout: break # Breaks the loop if the service is active
       time.sleep(3) # Waits before checking again
    except Exception as error:
        print(f'Error checking if httpd service is running: {error}')

print('!!! Running monitoring.sh...')
# Executes the monitoring.sh script on the EC2 instance
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} './monitoring.sh'"
    response = subprocess.run(command,shell=True)
    log_to_logs(f"Running monitoring.sh response: {response}") # Logs the response for running the script
except Exception as error:
    print (f'Error running monitoring.sh: {error}')

# Ends the logs
try: 
    with open('logs.txt','a') as file:
        file.write('//////////////////// END OF LOGS ////////////////////\n')
except Exception as error:
    print(f'Error writing to log file: {error}')

print('!!! END OF SCRIPT !!!')