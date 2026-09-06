import json
import boto3

ec2 = boto3.client('ec2')
bedrock_agent = boto3.client('bedrock-agent-runtime')

AGENT_ID = "ABCD1234"
AGENT_ALIAS_ID = "TSTALIAS1"

def lambda_handler(event, context):

    # Example alarm payload
    instance_id = "i-1234567890abcdef"

    # Get EC2 Details
    response = ec2.describe_instances(      InstanceIds=[instance_id]
    )

    instance = response['Reservations'][0]['Instances'][0]

    instance_type = instance['InstanceType']
    state = instance['State']['Name']

    prompt = f"""
    EC2 Instance ID: {instance_id}
    Instance Type: {instance_type}
    State: {state}

    CloudWatch Alarm:
    CPU Utilization exceeded 80%.

    Provide:
    1. Root Cause Analysis
    2. Recommended Actions
    3. AWS Best Practices
    """

    bedrock_response = bedrock_agent.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=context.aws_request_id,
        inputText=prompt
    )

    completion = ""

    for event_chunk in bedrock_response['completion']:
        if 'chunk' in event_chunk:
            completion += event_chunk['chunk']['bytes'].decode()

    print(completion)

    return {
        "statusCode": 200,
        "body": completion
    }
