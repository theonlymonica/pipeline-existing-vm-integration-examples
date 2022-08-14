import boto3
import os
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm_client = boto3.client('ssm')

document_name = os.environ["SSM_DOCUMENT"]
output_bucket = os.environ["OUTPUT_BUCKET"]

def lambda_handler(event, context):
    logger.info(event)

    instance_id = event["instance_id"]
    test_number = event["test_number"]
        
    response = ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters={"Message": [test_number]})

    command_id = response['Command']['CommandId']
    data = {
        "command_id": command_id, 
        "instance_id": instance_id
    }
    
    return data
