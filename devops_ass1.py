#!/usr/bin/env python3
import boto3, json, random, string, subprocess, datetime, time

ec2 = boto3.resource('ec2')
s3 = boto3.resource('s3')
s3client = boto3.client('s3')
key_name = 'EvaUnit00'
security_group = 'sg-0d2f8f0a77bd98152'
image_url = 'http://devops.witdemo.net/logo.jpg'

print('!!! START OF SCRIPT !!!\n!!! Creating log file...')
#https://www.pythontutorial.net/python-basics/python-write-text-file/
try: 
    with open('logs.txt','w') as file:
        file.write('//////////////////// START OF LOGS ////////////////////\n')
except Exception as error:
    print(f'Error while creating log file: {error}')

print('!!! Defining error logging method...')
def log_to_logs(log):
    try:
        with open('logs.txt', 'a') as file:
            #https://www.w3schools.com/python/python_datetime.asp
            file.write(f'{datetime.datetime.now()} : {log}\n')
    except Exception as error:
        print(f'Error writing to log file: {error}')

print('!!! Terminating previous instances (if any)...')
for instance in ec2.instances.all():
    if instance.state['Name'] == 'running':
        try:
            response = instance.terminate()
            log_to_logs(response)
        except Exception as error:
            print (f'Error while terminating previous instances: {error}')

print('!!! Emptying previous buckets (if any)...')
for bucket in s3.buckets.all():
    for key in bucket.objects.all():
        try:
            response = key.delete()
            log_to_logs(response)
        except Exception as error:
            print (f'Error while emptying previous buckets: {error}')

print('!!! Deleteing previous buckets (if any)...')
for bucket in s3.buckets.all():
    try:
        response = bucket.delete()
        log_to_logs(response)
    except Exception as error:
        print (f'Error while deleting previous buckets: {error}')

print('!!! Preparing new EC2 instance...')
try:
    new_instances = ec2.create_instances(
    ImageId='ami-0ebfd941bbafe70c6',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    KeyName=key_name,
    SecurityGroupIds=[security_group],#TODO ADD NEW AWS FUNCTION?
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

                cp index.html /var/www/html/index.html""")
    log_to_logs(response)
except Exception as error:
    print(f'Error creating EC2 instance: {error}\n!!! Stopping script...')
    exit()

print('!!! Preparing new EC2 instance\'s tags...')
try:
    response = new_instances[0].create_tags(
        Tags=[
            {
                'Key': 'Name',
                'Value': 'EvaUnit01'
            },
        ]
    )
    log_to_logs(response)
except Exception as error:
    print(f'Error while creating new instance\'s tags: {error}')

new_instances[0].wait_until_exists()
print (f'!!! Instance {new_instances[0].id} created successfully!\n!!! Waiting for instance to run...')
new_instances[0].wait_until_running()
print (f'!!! Instance {new_instances[0].id} is running! Visit the web page at: http://{new_instances[0].public_ip_address}\n!!! Writing website to freilly-websites.txt...')

try: 
    with open('freilly-websites.txt','w') as file:
        response = file.write(f'EC2 Instance: http://{new_instances[0].public_ip_address}')
    log_to_logs(response)        
except Exception as error:
    print(f'Error writing to website file: {error}')

print('!!! Creating S3 bucket...')
#https://stackoverflow.com/questions/2030053/how-to-generate-random-strings-in-python
try:
    new_bucket = s3.create_bucket(Bucket=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))+'-freilly')
    log_to_logs(response)
except Exception as error:
    print(f'Error creating S3 bucket: {error}\n!!! Stopping script...')
    exit()

print(f'!!! Configuring {new_bucket.name} website...')
website_configuration = {
 'ErrorDocument': {'Key': 'error.html'},
 'IndexDocument': {'Suffix': 'index.html'},
}

try:
    response = s3.BucketWebsite(new_bucket.name).put(WebsiteConfiguration=website_configuration)
    log_to_logs(response)
except Exception as error:
    print(f'Error putting website configuration into S3 bucket: {error}\n!!! Stopping script...')
    exit()

try:
    response = s3client.delete_public_access_block(Bucket=new_bucket.name)
    log_to_logs(response)
except Exception as error:
    print(f'Error deleting public access block for S3 bucket: {error}')

bucket_policy = {
    "Version": "2012-10-17",
    "Statement": 
    [
        {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": ["s3:GetObject"],
         "Resource": f"arn:aws:s3:::{new_bucket.name}/*"
         }
    ]
}

try:
    response = s3.Bucket(new_bucket.name).Policy().put(Policy=json.dumps(bucket_policy))
    log_to_logs(response)
except Exception as error:
    print(f'Error putting new policy into S3 bucket: {error}')

print(f'!!! Downloading image from {image_url}...')
try:
    response = subprocess.run(['curl','-O', image_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(response)
except Exception as error:
    print (f'Error downloading image from {image_url}: {error}')

print(f'!!! Uploading image from {image_url} to {new_bucket.name}...')
try:
    response = s3.Object(new_bucket.name,'logo.jpg').put(Body=open('logo.jpg','rb'),ContentType='image/jpeg')
    log_to_logs(response)
except Exception as error:
    print (f'Error uploading image from {image_url} to {new_bucket.name}: {error}')

print("!!! Creating index.html...")

#https://www.geeksforgeeks.org/creating-and-viewing-html-files-with-python/
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
        log_to_logs(response)
except Exception as error:
    print(f'Error creating index.html file: {error}')
    
print(f'!!! Uploading index.html to {new_bucket.name}...')
try:
    response = s3.Object(new_bucket.name,'index.html').put(Body=open('index.html','rb'),ContentType='text/html')
    log_to_logs(response)
except Exception as error:
 print (f'Error uploading index.html to {new_bucket.name}: {error}')

print(f'!!! {new_bucket.name} launched! Visit the web page at: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com\n!!! Writing website to freilly-websites.txt...')
try:
    with open('freilly-websites.txt','a') as file:
        response = file.write(f'\nS3 Bucket: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com')
    log_to_logs(response)
except Exception as error:
    print(f'Error writing to website file: {error}')

print(f'!!! Ensuring {key_name}.pem has correct permissions...')
try:
    command = f"chmod 400 {key_name}.pem"
    #https://stackoverflow.com/questions/11269575/how-to-hide-output-of-subprocess
    response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(response)
except Exception as error:
    print(f'Error ensuring {key_name}.pem has correct permissions: {error}')

print(f'!!! Copying monitoring.sh to {new_instances[0].public_ip_address}...')
try:
    command = f"scp -o StrictHostKeyChecking=no -i {key_name}.pem monitoring.sh ec2-user@{new_instances[0].public_ip_address}:."
    response = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_to_logs(response)
except Exception as error:
    print (f'Error copying monitoring.sh to {new_instances[0].public_ip_address}: {error}')

print('!!! Making monitoring.sh executable...')
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} 'chmod 700 monitoring.sh'"
    response = subprocess.run(command,shell=True)
    log_to_logs(response)
except Exception as error:
    print (f'Error making monitoring.sh executable: {error}\n!!! Stopping script...')
    exit()

print('!!! Waiting for EC2 web service to run...')
#https://www.tecmint.com/check-apache-httpd-status-and-uptime-in-linux/
while True:
    try:
       command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} 'systemctl is-active httpd'"
       response = subprocess.run(command, shell=True, capture_output=True, text=True)
       log_to_logs(response)
       if "inactive" not in response.stdout: break
       time.sleep(3)
    except Exception as error:
        print(f'Error checking if httpd service is running: {error}')

print('!!! Running monitoring.sh...')
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} './monitoring.sh'"
    response = subprocess.run(command,shell=True)
    log_to_logs(response)
except Exception as error:
    print (f'Error running monitoring.sh: {error}')

try: 
    with open('logs.txt','a') as file:
        file.write('//////////////////// END OF LOGS ////////////////////\n')
except Exception as error:
    print(f'Error writing to log file: {error}')

print('!!! END OF SCRIPT !!!')