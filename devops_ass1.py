#!/usr/bin/env python3
import boto3, json, random, string, sys

ec2 = boto3.resource('ec2')
s3 = boto3.resource("s3")
s3client = boto3.client("s3")
keyName = 'EvaUnit01'
securityGroup = 'sg-0d2f8f0a77bd98152'

print(f"!!! Terminating previous instances (if any)...")
for instance in ec2.instances.all():
    if instance.state['Name'] == 'running':
        response = instance.terminate()
        print(response)

print(f"!!! Emptying previous buckets (if any)...")
for bucket in s3.buckets.all():
    for key in bucket.objects.all():
        try:
            response = key.delete()
            print (response)
        except Exception as error:
            print (error)

print(f"!!! Deleteing previous buckets (if any)...")
for bucket in s3.buckets.all():
    try:
        response = bucket.delete()
        print(response)
    except Exception as error:
        print (error)


print(f"!!! Preparing new EC2 instance...")

new_instances = ec2.create_instances(
    ImageId='ami-0ebfd941bbafe70c6',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    KeyName=keyName,
    SecurityGroupIds=[securityGroup],
    UserData="""#!/bin/bash
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


print(f"!!! Preparing new EC2 instance's tags...")

new_instances[0].reload()
new_instances[0].create_tags(
    Tags=[
        {
            'Key': 'Name',
            'Value': 'EvaUnit01'
        },
    ]
)

new_instances[0].reload()
print (f'!!! Instance ' + new_instances[0].id + ' created sucessfully!\n!!! Waiting for instance to run...')
new_instances[0].wait_until_running()
new_instances[0].reload()
print (f'!!! Instance ' + new_instances[0].id + ' is running! Visit the web page at: http://' + new_instances[0].public_ip_address + '\n!!! Creating S3 bucket...')

#https://stackoverflow.com/questions/2030053/how-to-generate-random-strings-in-python
new_bucket = s3.create_bucket(Bucket=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))+"-freilly")

print(f'!!! Configuring ' + new_bucket.name + ' website...')

website_configuration = {
 'ErrorDocument': {'Key': 'error.html'},
 'IndexDocument': {'Suffix': 'index.html'},
}

s3.BucketWebsite(new_bucket.name).put(WebsiteConfiguration=website_configuration)

s3client.delete_public_access_block(Bucket=new_bucket.name)

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

s3.Bucket(new_bucket.name).Policy().put(Policy=json.dumps(bucket_policy))

print(f"!!! " + new_bucket.name + " launched! Visit the web page at: " + new_bucket.name + ".s3-website-us-east-1.amazonaws.com")