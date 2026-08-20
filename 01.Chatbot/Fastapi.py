print("✅ THIS IS THE CORRECT FILE LOADED")

from fastapi import FastAPI
from pydantic import BaseModel
from google import genai

app = FastAPI()

# Gemini Client
client = genai.Client(api_key="")

class RequestData(BaseModel):
    prompt: str
    max_length: int = 20


@app.post("/geminiask") #When someone sends a POST request to /geminiask, execute the function below.
async def generate_ans(data: RequestData):
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=data.prompt
        )
        return {
            "generated_text": response.text
        }
    except Exception as e:
        print("ERROR:", str(e))
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)