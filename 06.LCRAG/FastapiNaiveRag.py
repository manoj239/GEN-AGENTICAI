from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import ( ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings)
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import CrossEncoder
load_dotenv()
app = FastAPI()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
loader = PyPDFLoader("knowledge.pdf")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
chunks = splitter.split_documents(docs)
vectorstore = Chroma.from_documents(chunks,embeddings,persist_directory="chroma_db")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

class QueryRequest(BaseModel):
    question: str
    
@app.post("/ask") #RAG pipeline is exposed as an API endpoint.
async def ask_question(request: QueryRequest):
    query = request.question
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10}) #Async Operation 1
    docs = await retriever.ainvoke(query)  #retrieve the Top 10 similar chunks using vector similarity
    pairs = [(query, doc.page_content)  for doc in docs] 
    scores = reranker.predict(pairs) #    # Reranking Chunk1 = 0.85, Chunk2 = 0.91
    ranked_docs = sorted(zip(scores, docs), key=lambda x: x[0],reverse=True) #Sorting like Chunk5 = 0.94, Chunk2 = 0.91,Chunk1 = 0.85
    
    top_docs = [doc for score, doc in ranked_docs[:3]] # Result Chunk5, Chunk2, Chunk1
    
    context = "\n\n".join([doc.page_content for doc in top_docs])
    prompt = f"""
    Context:
    {context}

    Question:
    {query}

    Answer:
    """
    response = await llm.ainvoke(prompt) # Async Operation 2
    return {
        "question": query,
        "answer": response.content
    }

"""
First, I retrieved the top 10 candidate chunks from the vector database using semantic similarity
search. Then, I passed each query-document pair to a CrossEncoder reranker. The reranker
assigned a relevance score to every retrieved chunk by jointly evaluating the query and 
document content. I sorted the chunks based on those scores and selected the top 3 
highest-ranking chunks to build the final context passed to Gemini. This improved retrieval 
precision and reduced irrelevant context.

Architecture You Can Explain
User Query
      ↓
FastAPI Endpoint
      ↓
Pydantic Validation
      ↓
Retriever
(Top 10 Chunks)
      ↓
CrossEncoder Re-ranker
      ↓
Top 3 Chunks
      ↓
Context Builder
      ↓
Gemini 2.5 Flash
      ↓
JSON Response
``
"""
