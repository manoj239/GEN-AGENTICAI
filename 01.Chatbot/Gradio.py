import gradio as gr
import requests

#API_URL = "http://localhost:8000/generate"
API2_URL = "http://localhost:8000/geminiask"


def chat_fn(message, history):
    try:
        resp = requests.post(
            API2_URL,
            json={"prompt": message}
        )

        if resp.status_code == 200:
            return resp.json()["generated_text"]

        return f"Error {resp.status_code}: {resp.text}"

    except Exception as e:
        return f"API Error: {str(e)}"


gr.ChatInterface(
    fn=chat_fn,
    title="Manoj First Chatbot 🤖❤️"
).launch(
    server_name="0.0.0.0",
    server_port=7860,share=True
)

#access through ->http://localhost:7860/

200 -> Successful requests
201 -> Resource created
400 -> Bad request
401 -> Authentication required/failed
403 -> Forbidden
404 -> Resource/model not found
429 -> Too many requests. Quota exceeded.
500 -> Server-side error