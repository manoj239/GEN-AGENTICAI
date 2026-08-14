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

"""#1. Naive RAG
retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) 

query = input("Ask Question: ")

docs = retriever.invoke(query) #SIMILARITY SEARCH

context = "\n\n".join([doc.page_content for doc in docs])

prompt = f"""
Context:
{context}

Question:
{query}

Answer:
"""

response = llm.invoke(prompt)

print(response.content)

#Question
# ↓
#Embedding Model
# ↓
#Query Vector
# ↓
#Similarity Search
# ↓
#Top K(3) Chunks
This part is automatically handled.

RAG is:
retrieve relevant chunks
       +
user query
       +
LLM


#2. Hybrid RAG
query = input("Ask Question: ")

vector_results = vectorstore.similarity_search( query, k=2) #Cosine Similarity

keyword_results = []
query_words = query.lower().split()
for chunk in chunks:
    chunk_text = chunk.page_content.lower()
    for word in query_words:
        if word in chunk_text:
            keyword_results.append(chunk)
            break

all_results = vector_results + keyword_results

context = "\n\n".join([doc.page_content for doc in all_results])

response = llm.invoke(
    f"""
    Context:
    {context}

    Question:
    {query}

    Answer:
    """
)

print(response.content)
#Vector Search + Keyword Search=Hybrid RAG
    #Architecture
    
                  User Query
                   │
        ┌──────────┴──────────┐
        │                     │
 Vector Similarity      Keyword Search
        │                     │
        └──────────┬──────────┘
                   │
            Merge Results
                   │
             Build Context
                   │
                  LLM
                   │
                Answer

#3. Agentic RAG: Decides between:RAG or Web Search. Agent decides which tool to use.
from langchain_community.utilities import GoogleSerperAPIWrapper

search = GoogleSerperAPIWrapper()
query = input("Ask Question: ")
router_prompt = f"""
You are a routing agent.
Decide whether the question should use:
1. RAG
    - Internal company knowledge
    - PDF knowledge base
    - Documentation
2. WEB
    - Latest events
    - Current news
    - Real-time information
Question:
{query}
Reply only:
RAG
or
WEB
"""
decision = llm.invoke(router_prompt).content.strip().upper()
print("Decision:", decision)
# Route
if decision == "WEB":
    print("Using Web Search...")
    context = search.run(query)
else:
    print.similarity_search(query,k=3)
    context = "\n\n".join([doc.page_content for doc in docs]
    )
# Final Answer
response = llm.invoke(
    f"""
    Context:
    {context}
    Question:
    {query}
    Answer:
    """
)
print("\n====== ANSWER ======\n")
print(response.content)


#4. Corrective RAG (CRAG)
from langchain_community.utilities import GoogleSerperAPIWrapper

search = GoogleSerperAPIWrapper()

query = input("Ask Question: ")

results = vectorstore.similarity_search_with_score(query, k=3)

best_doc, best_score = results[0]

if best_score > 1:

    print("Poor retrieval. Using Web Search.")

    context = search.run(query)

else:

    context = "\n\n".join(
        [doc.page_content for doc, score in results]
    )

response = llm.invoke(
    f"""
    Context:
    {context}

    Question:
    {query}

    Answer:
    """
)

print(response.content)

Interview note:
    Validate Retrieval
        ↓
Good? → Use RAG
Bad?  → Use Web Search

#5. Self-RAG: LLM evaluates the retrieved context itself.
from langchain_community.utilities import GoogleSerperAPIWrapper

search = GoogleSerperAPIWrapper()

query = input("Ask Question: ")

docs = vectorstore.similarity_search(query, k=3)

context = "\n\n".join(
    [doc.page_content for doc in docs]
)

evaluation = llm.invoke(
    f"""
    Question:
    {query}

    Context:
    {context}

    Is this context sufficient
    to answer the question?

    Reply only YES or NO.
    """
)

decision = evaluation.content.strip().lower()

if "no" in decision:

    print("LLM says context insufficient.")

    web_context = search.run(query)

    context = context + "\n\n" + web_context

response = llm.invoke(
    f"""
    Context:
    {context}

    Question:
    {query}

    Answer:
    """
)

print(response.content)

#6. Reranking RAG
from sentence_transformers import CrossEncoder

query = input("Ask Question: ")

# Retrieve more chunks initially
docs = vectorstore.similarity_search(
    query,
    k=10
)

# Reranker Model
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# Create Query-Document Pairs
pairs = [
    (query, doc.page_content)
    for doc in docs
]

# Generate Relevance Scores
scores = reranker.predict(pairs)

# Sort Documents by Score
ranked_docs = sorted(
    zip(docs, scores),
    key=lambda x: x[1],
    reverse=True
)

print("\n=== RERANKED RESULTS ===\n")

for i, (doc, score) in enumerate(ranked_docs[:3]):
    print(f"Rank {i+1}")
    print("Score:", score)
    print(doc.page_content[:300])
    print("-" * 50)

# Keep only Top 3 Reranked Chunks
top_docs = [
    doc
    for doc, score in ranked_docs[:3]
]

context = "\n\n".join(
    [doc.page_content for doc in top_docs]
)

response = llm.invoke(
    f"""
    Context:
    {context}

    Question:
    {query}

    Answer:
    """
)

print(response.content)

With Reranking
Question
    ↓
Vector Search (k=10)
    ↓
Reranker
    ↓
Best 3 Chunks
    ↓
Gemini

Most Important for Interviews. Focus on these explanations:
Naive RAG=Retriever + LLM
Hybrid RAG=Vector Search + Keyword Search
Agentic RAG=Agent chooses tool
CRAG=Validate retrieval quality
Self-RAG=LLM validates retrieval quality


The document ingestion pipeline remains largely the same across RAG architectures: loading,
chunking, embedding generation, and vector storage. The primary difference lies in the 
retrieval and decision-making layer. Naive RAG performs simple retrieval, Hybrid RAG 
combines vector and keyword search, Agentic RAG uses agents and tools, CRAG validates 
retrieval quality and corrects failures, and Self-RAG uses the LLM itself to assess retrieval 
sufficiency.
"""