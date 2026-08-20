from dotenv import load_dotenv
from langchain_google_genai import (ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings)
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
loader = PyPDFLoader("knowledge.pdf")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
chunks = splitter.split_documents(docs)
vectorstore = Chroma.from_documents(documents=chunks,embedding=embeddings, persist_directory="chroma_db")
retriever = vectorstore.as_retriever(search_kwargs={"k":3})
query = input("Ask Question : ")
retrieved_docs = retriever.invoke(query)
context = "\n\n".join(
    [doc.page_content for doc in retrieved_docs])
prompt = f"""
Answer the question only from the context.

If answer does not exist in context,
say:

I cannot find the answer.

Context:

{context}

Question:

{query}
"""
response = llm.invoke(prompt)

print("\nAnswer:")
print(response.content)

"""
                  #Pinecone Vector Store Example
from langchain_pinecone import PineconeVectorStore

vectorstore = PineconeVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    index_name="my-index"
)
retriever = vectorstore.as_retriever()

retriever.invoke(query)

                    #FAISS Vector Store Example
from langchain_community.vectorstores import FAISS

vectorstore = FAISS.from_documents(
    chunks,
    embeddings
)
retriever = vectorstore.as_retriever()
"""
