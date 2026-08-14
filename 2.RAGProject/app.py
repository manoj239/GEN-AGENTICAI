import os
import PyPDF2
import chromadb

from google import genai
from chromadb.utils import embedding_functions


# ==================================
# PDF READER
# ==================================

def read_pdf_file(file_path):

    text = ""

    with open(file_path, "rb") as file:

        pdf_reader = PyPDF2.PdfReader(file)

        for page in pdf_reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text


# ==================================
# TEXT CHUNKING
# ==================================

def split_text(text, chunk_size=500):

    sentences = text.replace("\n", " ").split(". ")

    chunks = []

    current_chunk = []
    current_size = 0


    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue


        if not sentence.endswith("."):
            sentence += "."


        size = len(sentence)


        if current_size + size > chunk_size and current_chunk:

            chunks.append(
                " ".join(current_chunk)
            )

            current_chunk = [sentence]

            current_size = size


        else:

            current_chunk.append(sentence)

            current_size += size


    if current_chunk:

        chunks.append(
            " ".join(current_chunk)
        )


    return chunks



# ==================================
# CHROMADB SETUP
# ==================================

client_db = chromadb.PersistentClient(
    path="./chroma_db"
)


embedding_fn = (
    embedding_functions
    .SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
)



# Delete old collection for fresh testing

try:

    client_db.delete_collection(
        "documents_collection"
    )

except:

    pass



collection = client_db.get_or_create_collection(

    name="documents_collection",

    embedding_function=embedding_fn

)



# ==================================
# LOAD PDF
# ==================================

pdf_path = "./docs/RAG_Test_Knowledge_Base.pdf"


content = read_pdf_file(pdf_path)


chunks = split_text(content)



file_name = os.path.basename(pdf_path)



ids = [

    f"{file_name}_chunk_{i}"

    for i in range(len(chunks))

]



metadatas = [

    {
        "source": file_name,
        "chunk": i
    }

    for i in range(len(chunks))

]



collection.add(

    documents=chunks,

    metadatas=metadatas,

    ids=ids

)



print(
    f"\n✅ Loaded {len(chunks)} chunks"
)



# ==================================
# GEMINI SETUP
# ==================================

gemini_client = genai.Client(

    api_key="AQ.Ab8RN6K9PsCd0HFGdWvhFkhNEXvHjYnIcLv99xPNKgymkWwwtg"

)



# ==================================
# RAG LOOP
# ==================================

while True:


    query = input(
        "\nAsk Question (or type quit): "
    )


    if query.lower() == "quit":

        break



    # Retrieve relevant chunks

    results = collection.query(

        query_texts=[query],

        n_results=2,

        include=[
            "documents",
            "metadatas"
        ]

    )



    context = "\n\n".join(

        results["documents"][0]

    )



    prompt = f"""

You are a helpful AI assistant.

Answer ONLY using the context provided below.


If the answer is not present in the context,
respond exactly:

I cannot answer this from the provided documents.


Context:

{context}



Question:

{query}



Answer:

"""



    response = gemini_client.models.generate_content(

        model="gemini-2.0-flash",

        contents=prompt

    )



    print("\n✅ Answer:")

    print(response.text)



    print("\n✅ Sources:")



    for meta in results["metadatas"][0]:

        print(

            f"- {meta['source']} "
            f"(chunk {meta['chunk']})"

        )