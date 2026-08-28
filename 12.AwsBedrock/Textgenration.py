import boto3
import json

bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({
        "messages": [
            {
                "role": "user",
                "content": "Explain RAG in simple terms"
            }
        ],
        "max_tokens": 300,
        "anthropic_version": "bedrock-2023-05-31"
    })
)

result = json.loads(response["body"].read())

print(result)

""""
O/p:
    RAG stands for Retrieval-Augmented Generation.
    Instead of using only model knowledge,
    RAG retrieves relevant documents
    and uses them as context before
    generating the answer.
""""""

This code demonstrates how to invoke a foundation model hosted in Amazon Bedrock. Using the 
Bedrock Runtime API, a prompt is sent to Claude Sonnet, and the generated response is returned. 
This is the typical approach used to build chatbots, assistants, summarization systems, and GenAI
applications on AWS.
"""