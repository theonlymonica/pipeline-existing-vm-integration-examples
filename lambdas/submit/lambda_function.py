import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm_client = boto3.client('ssm')

document_name = os.environ["SSM_DOCUMENT"]
output_bucket = os.environ["OUTPUT_BUCKET"]
code_repository = os.environ["CODE_REPOSITORY"]

def lambda_handler(event, context):
    logger.debug(event)

    instance_id = event["instance_id"]
    message = event["message"]
        
    response = ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters={
                    "Message": [message],
                    "OutputBucket": [output_bucket],
                    "CodeRepository": [code_repository]})
    
    logger.debug(response)

    command_id = response['Command']['CommandId']
    data = {
        "command_id": command_id, 
        "instance_id": instance_id
    }
    
    return data
