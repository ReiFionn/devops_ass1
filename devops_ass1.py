#!/usr/bin/env python3
import boto3, json, random, string, subprocess, datetime

ec2 = boto3.resource('ec2')
s3 = boto3.resource('s3')
s3client = boto3.client('s3')
key_name = 'EvaUnit00'
security_group = 'sg-0d2f8f0a77bd98152'
image_url = 'http://devops.witdemo.net/logo.jpg'

print('!!! Creating log file...')
#https://www.pythontutorial.net/python-basics/python-write-text-file/
try: 
    with open('logs.txt','w') as file:
        file.write('//////////////////// START OF LOGS ////////////////////\n')
except Exception as error:
    print(error)

print('!!! Terminating previous instances (if any)...')
for instance in ec2.instances.all():
    if instance.state['Name'] == 'running':
        try:
            response = instance.terminate()
            try:
                with open('logs.txt','a') as file:
                    #https://www.w3schools.com/python/python_datetime.asp
                    file.write(f'{datetime.datetime.now()} : {response}')
            except Exception as error:
                print(error)
        except Exception as error:
            print (error)

print('!!! Emptying previous buckets (if any)...')
for bucket in s3.buckets.all():
    for key in bucket.objects.all():
        try:
            response = key.delete()
            #print (response)
        except Exception as error:
            print (error)

print('!!! Deleteing previous buckets (if any)...')
for bucket in s3.buckets.all():
    try:
        response = bucket.delete()
        #print(response)
    except Exception as error:
        print (error)

print('!!! Preparing new EC2 instance...')
try:
    new_instances = ec2.create_instances(
    ImageId='ami-0ebfd941bbafe70c6',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    KeyName=key_name,
    SecurityGroupIds=[security_group],
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
except Exception as error:
    print(error)

print('!!! Preparing new EC2 instancet\'s tags...')

try:
    new_instances[0].create_tags(
        Tags=[
            {
                'Key': 'Name',
                'Value': 'EvaUnit01'
            },
        ]
    )
except Exception as error:
    print(error)

new_instances[0].reload()
print (f'!!! Instance {new_instances[0].id} created sucessfully!\n!!! Waiting for instance to run...')
new_instances[0].wait_until_running()
new_instances[0].reload()
print (f'!!! Instance {new_instances[0].id} is running! Visit the web page at: http://{new_instances[0].public_ip_address}\n!!! Writing website to freilly-websites.txt...')

try: 
    with open('freilly-websites.txt','w') as file:
        file.write(f'EC2 Instance: http://{new_instances[0].public_ip_address}')
except Exception as error:
    print(error)

print('!!! Creating S3 bucket...')
#https://stackoverflow.com/questions/2030053/how-to-generate-random-strings-in-python
try:
    new_bucket = s3.create_bucket(Bucket=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))+'-freilly')
except Exception as error:
    print(error)

print(f'!!! Configuring {new_bucket.name} website...')
website_configuration = {
 'ErrorDocument': {'Key': 'error.html'},
 'IndexDocument': {'Suffix': 'index.html'},
}

try:
    s3.BucketWebsite(new_bucket.name).put(WebsiteConfiguration=website_configuration)
except Exception as error:
    print(error)

try:
    s3client.delete_public_access_block(Bucket=new_bucket.name)
except Exception as error:
    print(error)

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
    s3.Bucket(new_bucket.name).Policy().put(Policy=json.dumps(bucket_policy))
except Exception as error:
    print(error)

print(f'!!! Downloading image from {image_url}...')
try:
    response = subprocess.run(['curl','-O', image_url])
    #print(response)
except Exception as error:
    print (error)

print(f'!!! Uploading image from {image_url} to {new_bucket.name}...')
try:
    response = s3.Object(new_bucket.name,'logo.jpg').put(Body=open('logo.jpg','rb'),ContentType='image/jpeg')
    #print(response)
except Exception as error:
    print (error)

print("!!! Creating index.html...")

#https://www.geeksforgeeks.org/creating-and-viewing-html-files-with-python/
try:
    with open('index.html','w') as file:
        file.write(f"""<html>
        <head>
            <title>{new_bucket.name}'s Website!</title>
        </head>
        <body>
            <h2>Here is the image from {image_url}!</h2>
            <img src="http://{new_bucket.name}.s3.amazonaws.com/logo.jpg" alt="Looks like it didn't work LOL!">
            <p>Isn't it great! :D</p>
        </body>
        </html>""")
except Exception as error:
    print(error)
    
print(f'!!! Uploading index.html to {new_bucket.name}...')
try:
    response = s3.Object(new_bucket.name,'index.html').put(Body=open('index.html','rb'),ContentType='text/html')
    #print(response)
except Exception as error:
 print (error)

print(f'!!! {new_bucket.name} launched! Visit the web page at: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com\n!!! Writing website to freilly-websites.txt...')
with open('freilly-websites.txt','a') as file:
    file.write(f'\nS3 Bucket: http://{new_bucket.name}.s3-website-us-east-1.amazonaws.com')

print(f'!!! Copying monitoring.sh to {new_instances[0].public_ip_address}...')
try:
    command = f"scp -o StrictHostKeyChecking=no -i {key_name}.pem monitoring.sh ec2-user@{new_instances[0].public_ip_address}:."
    response = subprocess.run(command, shell=True)
except Exception as error:
    print (error)

print('!!! Making monitoring.sh executable...')
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} 'chmod 700 monitoring.sh'"
    response = subprocess.run(command,shell=True)
except Exception as error:
    print (error)

print('!!! Running monitoring.sh...')
try:
    command = f"ssh -i {key_name}.pem ec2-user@{new_instances[0].public_ip_address} './monitoring.sh'"
    response = subprocess.run(command,shell=True,capture_output=True,text=True)
    print(response.stdout.strip())
except Exception as error:
    print (error)

print('!!! END OF SCRIPT !!!')