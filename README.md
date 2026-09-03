# GEN-AI / AI Projects Portfolio

This repository is a hands-on collection of GenAI, LLM, RAG, agent, workflow, and cloud integration experiments. It contains a mix of learning exercises, proof-of-concepts, and mini projects that demonstrate practical usage of modern AI tools and frameworks.

I have built and explored multiple GenAI patterns, starting from simple chatbot applications to more advanced RAG, orchestration, and multi-agent systems. My work includes prompt engineering, vector search, structured outputs, workflow automation, and cloud AI integration. This shows both foundational understanding and hands-on implementation experience across the LLM ecosystem.

The goal of this repo is to build understanding across the full AI stack:

- Prompt design and LLM usage
- Retrieval-Augmented Generation (RAG)
- Structured outputs and schema validation
- LangChain and LangGraph patterns
- Multi-agent orchestration
- MCP-based integrations
- Workflow automation with n8n
- Cloud AI using AWS Bedrock

---

## Repository Structure

### 01. Chatbot
Focus: Building an AI chatbot with Gradio and FastAPI.

Includes:
- Gradio frontend for chat UI
- FastAPI backend service
- Google Gemini integration
- Request/response pipeline
- Basic AI app architecture for interview demos

This is a good example of a simple LLM-powered conversational application.

### 02. RAGProject
Focus: Retrieval-Augmented Generation using PDF documents.

Includes:
- PDF ingestion and text extraction
- Chunking logic for documents
- ChromaDB vector database
- Embedding generation using SentenceTransformers
- Semantic search + Gemini-powered Q&A

This demonstrates how to build a knowledge-base chatbot that answers using uploaded documents.

### 03. LangchainIntro
Focus: Core LangChain concepts and practical model usage.

Includes:
- Chat model integrations
  - OpenAI
  - Anthropic
  - Google Gemini
  - Hugging Face API
  - Local Hugging Face models
- Embedding examples
  - OpenAI embeddings
  - Gemini embeddings
  - Hugging Face local embeddings
  - Document similarity examples

This folder covers the fundamentals of using LangChain for LLM apps and embeddings.

### 04. Prompttemplate
Focus: Prompt engineering and prompt templates.

Includes:
- General prompt patterns
- PromptTemplate usage
- Dynamic prompt generation
- ChatPromptTemplate with message history
- Temperature parameter experiments

This folder shows how prompt quality and model behavior can be controlled effectively.

### 05. StructuredOutput
Focus: Producing structured outputs from LLMs.

Includes:
- TypedDict-based structured responses
- Annotated schema patterns
- Pydantic model-based structured outputs

This demonstrates how to instruct LLMs to return JSON or strongly typed data suitable for apps and workflows.

### 06. LCRAG
Focus: Local/custom RAG pipelines and retrieval workflows.

Includes:
- Common RAG implementations
- Custom RAG flow
- Gemini-powered RAG pipeline examples
- Server-based RAG app pipeline

This folder focuses on practical RAG patterns beyond just basic retrieval and generation.

### 07. Python
Focus: Python practice and data analysis basics.

Includes:
- Pandas notebook exercises
- CSV data analysis
- Python practice notebooks

This section shows foundational Python and data handling skills used in AI projects.

### 08. LangGraph
Focus: Graph-based workflow orchestration and agent workflows.

Includes:
- Intro to LangGraph
- Parallelization patterns
- Routing logic
- Orchestration flow
- Agent execution
- Streaming responses

This folder demonstrates how to design multi-step AI systems with state, branching, and coordination.

### 09. MCP
Focus: Model Context Protocol examples and custom integrations.

Includes:
- Local MCP server examples
- Remote MCP server examples
- Custom MCP client implementation
- JSON-based configuration for tools and integrations

This shows how AI agents can connect to external tools and services in a standardized way.

### 10. n8n
Focus: Workflow automation and process integration.

Includes:
- Form submission workflow proof-of-concept
- Alerting workflow
- CI/CD automation examples

This folder highlights automation skills and connecting AI workflows with business operations.

### 11. Crewai
Focus: Multi-agent collaboration using CrewAI.

Includes:
- Agent with tools script
- Manager-worker hierarchy pattern
- Peer-to-peer agent collaboration
- Environment configuration for API keys
- Setup and usage instructions

This is a strong example of agent-based systems with delegation, research, and coordinated work.

### 12. AwsBedrock
Focus: AWS Bedrock integration.

Includes:
- Text generation using AWS Bedrock
- Titan embeddings example

This demonstrates cloud-based generative AI using enterprise AI services.

---

## Interview-Ready Highlights

These are the main proof-of-concepts that can be discussed in interviews:

- Built a chatbot using Gradio + FastAPI + Gemini
- Implemented RAG over PDFs with vector search and embeddings
- Worked with LangChain for LLM orchestration and embedding workflows
- Built prompt templates and dynamic prompting strategies
- Generated structured JSON outputs from LLMs using TypedDict/Pydantic
- Designed LangGraph workflows for routing, orchestration, and streaming
- Built multi-agent systems using CrewAI
- Connected AI systems with MCP tools and servers
- Automated business workflows using n8n
- Integrated enterprise AI using AWS Bedrock

---

## Skills Demonstrated

This repo reflects hands-on experience with:

- Python
- FastAPI
- Gradio
- LangChain
- LangGraph
- ChromaDB
- Hugging Face
- OpenAI / Gemini / Anthropic APIs
- Prompt engineering
- RAG architecture
- Agentic AI patterns
- MCP and tool integration
- Workflow automation
- AWS AI services

---

## Summary

This repository is a full-spectrum GenAI learning and experimentation project covering the most important AI patterns used in real-world applications today. It is a strong portfolio foundation for interviews, AI projects, and future production implementation work.
