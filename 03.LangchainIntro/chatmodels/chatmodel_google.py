from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

model = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

result = model.invoke('What is the purpose of Generative AI')

print(result.content)




"""
from langchain_google_genai import ChatGoogleGenerativeAI
import os
os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6IPW5J1OacLx0XzbhKtZc-pTIk9nanqIBSG8qQppKjUUg"

# Initialize model
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Run query
result = model.invoke("What is the purpose of Generative AI")

# Print output
print(result.content)
"""
