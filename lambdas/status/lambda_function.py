import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm_client = boto3.client('ssm')

def lambda_handler(event, context):
    
    instance_id = event['Payload']['instance_id']
    command_id = event['Payload']['command_id']
    
    logger.info(instance_id)
    logger.info(command_id)

    response = ssm_client.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    logger.info(response)
    
    execution_status = response['StatusDetails']
    logger.info(execution_status)

    if execution_status == "Success":
        return {"status": "SUCCEEDED", "event": event}
    elif execution_status in ('Pending', 'InProgress', 'Delayed'):
        data = {
            "command_id": command_id, 
            "instance_id": instance_id,
            "status": "RETRY", 
            "event": event
        }
        return data
    else:
        return {"status": "FAILED", "event": event}
