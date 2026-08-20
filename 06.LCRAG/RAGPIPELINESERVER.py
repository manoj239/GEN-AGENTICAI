from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import GoogleSerperAPIWrapper
load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, max_output_tokens=512)
search = GoogleSerperAPIWrapper() # Google Serper Search

query = input("Ask Question: ")## User Question

web_result = search.run(query) #Web Search
print("\nWEB SEARCH RESULTS\n")
print(web_result)

# Prompt
prompt = f"""
Answer the user's question using the web search results below.

Web Search Results:
{web_result}

Question:
{query}

Answer:
"""

# Gemini Response
response = llm.invoke(prompt)

print("\nFINAL ANSWER:\n")
print(response.content)
    
    
"""
results = vectorstore.similarity_search_with_score(
    query,
    k=3
)

best_doc, best_score = results[0]

if best_score > 1.0:

    web_result = search.run(query)

    prompt = f"""
    Answer using the web search result.

    Context:
    {web_result}

    Question:
    {query}
    """

else:

    context = "\n\n".join(
        [doc.page_content for doc, score in results]
    )

    prompt = f"""
    Answer using the provided context.

    Context:
    {context}

    Question:
    {query}
    """

response = llm.invoke(prompt)

print(response.content)

User Question
      │
      ▼
   Chroma
      │
      ▼
Similarity Score
      │
 ┌────┴────┐
 │         │
Good     Poor
Match    Match
 │         │
 ▼         ▼
RAG     Web Search
 │         │
 └────┬────┘
      ▼
   Gemini
      ▼
   Answer
"""
