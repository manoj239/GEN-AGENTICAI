# AI Chatbot using Gradio, FastAPI and Google Gemini

## Overview

This project is a simple AI chatbot built using:

- Gradio (Frontend/UI)
- FastAPI (Backend API)
- Google Gemini LLM
- Uvicorn (Web Server)

The chatbot allows users to enter questions through a web interface and receive AI-generated responses from Google's Gemini model.

---

## Architecture

User
↓
Gradio UI
↓
HTTP Request
↓
FastAPI Backend
↓
Gemini LLM
↓
FastAPI Response
↓
Gradio UI
↓
User

---

## Components

### 1. Gradio

Gradio is used to create the chatbot user interface.

Responsibilities:

- Accept user questions
- Display chatbot responses
- Send requests to FastAPI

Example:

User enters:

What is AWS?

Gradio sends:

{
    "prompt": "What is AWS?"
}

to the FastAPI backend.

---

### 2. FastAPI

FastAPI acts as the backend service.

Responsibilities:

- Receive requests from Gradio
- Validate incoming data
- Call Gemini API
- Return response back to Gradio

Endpoint:

POST /geminiask

URL:

http://localhost:8000/geminiask

---

### 3. Pydantic

Pydantic is used for request validation.

Example:

class RequestData(BaseModel):
    prompt: str

This ensures the API receives the expected data format.

---

### 4. Gemini

Gemini is the Large Language Model (LLM).

Responsibilities:

- Understand user prompts
- Generate intelligent responses
- Return generated text

Example:

Prompt:

What is AWS?

Response:

AWS is Amazon Web Services...

---

### 5. Uvicorn

Uvicorn is the server used to run FastAPI.

Example:

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000
)

Responsibilities:

- Listen for incoming requests
- Route requests to FastAPI
- Return responses

---

## Workflow

Step 1

User enters a question in Gradio.

Example:

What is AWS?

↓

Step 2

Gradio sends an HTTP POST request to FastAPI.

↓

Step 3

FastAPI receives the request.

↓

Step 4

Pydantic validates the request data.

↓

Step 5

FastAPI sends the prompt to Gemini.

↓

Step 6

Gemini generates a response.

↓

Step 7

FastAPI returns the generated text.

↓

Step 8

Gradio displays the answer.

---

## Request Flow Example

User:

What is AWS?

↓

Gradio

↓

POST /geminiask

{
    "prompt": "What is AWS?"
}

↓

FastAPI

↓

Gemini

↓

Response:

AWS is a cloud computing platform provided by Amazon.

↓

Gradio

↓

User sees the response.

---

## Running the Application

### Start FastAPI

python Testing1.py

This starts:

http://localhost:8000

---

### Start Gradio

python Gradio.py

This starts:

http://localhost:7860

---

## Technologies Used

- Python
- FastAPI
- Uvicorn
- Gradio
- Pydantic
- Google Gemini API

---

FastAPI acts as the middleware between the frontend and the LLM.
Gradio provides the chatbot user interface.
Pydantic validates incoming request data.
Uvicorn runs the FastAPI application and listens for HTTP requests.
Gemini generates responses based on user prompts.
This project demonstrates API development, frontend-backend communication, and LLM integration.

## Future Enhancements

- Conversation Memory
- Web Search Integration
- LangChain
- LangGraph
- RAG (Retrieval Augmented Generation)
- Vector Database Integration
- User Authentication
- Deployment on AWS EC2