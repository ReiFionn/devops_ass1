#!/usr/bin/env python3
import boto3
import sys

ec2 = boto3.resource('ec2')
s3 = boto3.resource("s3")

print("Preparing EC2 instance...")

new_instances = ec2.create_instances(
    ImageId='ami-0ebfd941bbafe70c6',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    KeyName='EvaUnit00',
    SecurityGroupIds=['sg-00cdb324bcc33e972'],
    UserData="""#!/bin/bash
 yum install httpd -y
 systemctl enable httpd
 systemctl start httpd""")

print("Preparing new EC2 instance's tags...")

new_instances[0].create_tags(
    Tags=[
        {
            'Key': 'Name',
            'Value': 'EvaUnit00'
        },
    ]
)

print ('Instance ' + new_instances[0].id + ' created sucessfully!\nWaiting for instance to run...')
new_instances[0].wait_until_running()
print ('Instance ' + new_instances[0].id + ' is running! Visit the web page at: http://' + new_instances[0].public_ip_address + '\nCreating S3 bucket...')

new_bucket = s3.create_bucket(Bucket="87vwe6-freilly")

website_configuration = {
 'ErrorDocument': {'Key': 'error.html'},
 'IndexDocument': {'Suffix': 'index.html'},
}

print('Configuring ' + new_bucket.name + ' website...')

bucket_website = s3.BucketWebsite(new_bucket.name).put(WebsiteConfiguration=website_configuration)

print(new_bucket.name + " launched!")