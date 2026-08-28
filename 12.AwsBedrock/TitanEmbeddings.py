import boto3
import json

client = boto3.client( "bedrock-runtime",region_name="us-east-1")

response = client.invoke_model( modelId="amazon.titan-embed-text-v2:0",
                               body=json.dumps({
"inputText": "What is Generative AI?"
})
)

embedding = json.loads( response["body"].read())

print(len(embedding["embedding"]))

"""
How This Fits Inside RAG
PDF
 ↓
Chunking
 ↓
Titan Embeddings
 ↓
ChromaDB
 ↓
User Question
 ↓
Titan Embeddings
 ↓
Similarity Search
 ↓
Relevant Chunks
 ↓
Claude
 ↓
Answer


This code demonstrates how to generate embeddings using the Amazon Titan Embeddings model available
in AWS Bedrock. Instead of generating a text response like Claude, the Titan model converts the 
input text into a numerical vector representation called an embedding. These embeddings capture
the semantic meaning of the text and are commonly used in RAG applications, semantic  search, 
recommendation systems, and vector databases. In this example, the text "What is Generative AI?" is
sent to the Titan Embeddings model through the Bedrock Runtime API. The model returns a 
high-dimensional vector, which can then be stored in vector databases such as ChromaDB, 
Pinecone, FAISS, or OpenSearch. Later, when a user asks a question, the same embedding model 
converts the query into a vector, and similarity search is performed to find the most relevant 
documents. Those retrieved documents are then passed to an LLM like Claude or Gemini to generate
the final response.In a typical RAG architecture, Titan Embeddings are responsible for the 
retrieval layer, while models such as Claude are responsible for the generation layer.
"""

