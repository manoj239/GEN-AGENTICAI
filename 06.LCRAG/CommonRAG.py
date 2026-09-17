from dotenv import load_dotenv
from langchain_google_genai import (ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings)
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from sentence_transformers import CrossEncoder
from langchain_text_splitters import (RecursiveCharacterTextSplitter, CharacterTextSplitter,Language )
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import (DirectoryLoader,WebBaseLoader)

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

loader = PyPDFLoader("knowledge.pdf") #Data Ingestion
#loader = WebBaseLoader("https://en.wikipedia.org/wiki/Amazon_Web_Services")
#loader = DirectoryLoader(
#    path="books",
#    glob="*.pdf",
#    loader_cls=PyPDFLoader
#)

docs = loader.load()
#docs = loader.lazy_load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
#splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
#splitter = SemanticChunker(embeddings,breakpoint_threshold_type="standard_deviation",breakpoint_threshold_amount=1)
#splitter= RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON,chunk_size=500)
chunks = splitter.split_documents(docs)

vectorstore = Chroma.from_documents(chunks, embeddings,persist_directory="chroma_db")
#vectorstore = PineconeVectorStore.from_documents(documents=chunks, embedding=embeddings, index_name="rag-index")
#vectorstore = FAISS.from_documents(chunks, embeddings)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

"""
RAG ARCHITECTURES DOCUMENTATION
================================

1. NAIVE RAG: Retriever + LLM
   - Simple vector similarity search
   - Direct context injection into LLM
   - Process: Query → Embedding → Vector Search → Top K chunks → LLM

2. HYBRID RAG: Vector Search + Keyword Search
   - Combines semantic (vector) and lexical (keyword) retrieval
   - Merges results from both approaches
   - Better recall and precision

3. AGENTIC RAG: Agent-based routing
   - Agent decides between RAG or Web Search
   - Dynamic tool selection based on query type
   - Handles both internal knowledge and real-time information

4. CORRECTIVE RAG (CRAG): Quality validation
   - Validates retrieval quality with relevance scoring
   - Falls back to web search if retrieval score is poor
   - Improves result accuracy

5. SELF-RAG: LLM-based evaluation
   - LLM evaluates if retrieved context is sufficient
   - Automatically augments with web search if needed
   - Self-correcting retrieval mechanism

6. RERANKING RAG: Result optimization
   - Initial retrieval with higher k (more chunks)
   - Rerank results using cross-encoder model
   - Select top K reranked results for LLM
   - Better relevance through secondary ranking

KEY INTERVIEW POINTS:
- Document ingestion pipeline is consistent across all RAG types
- Main differences are in retrieval and decision-making layers
- Each variant addresses specific limitations of simpler approaches
- Complexity increases with sophistication (Naive → Self-RAG/Reranking)
"""