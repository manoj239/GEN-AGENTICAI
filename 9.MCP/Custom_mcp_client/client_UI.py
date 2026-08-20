import asyncio
import json
import streamlit as st
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage

# pip install streamlit langchain langchain-mcp-adapters langchain-google-genai python-dotenv
#streamlit run client_UI.py


# Load env vars
load_dotenv()

SERVERS = {
    "expense_local_server": {
        "transport": "stdio",
        "command": "H:\\01_Training\\ContentSlides_AgenticAI\\Code\\MCP\\Custom_local_mcp-server\\.venv\\Scripts\\python.exe",
        "args": [
            "H:\\01_Training\\ContentSlides_AgenticAI\\Code\\MCP\\Custom_local_mcp-server\\main.py"
        ],
        "env": {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1"
        }
    }
}

# Async MCP execution
async def run_query(user_query: str):
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()
    named_tools = {tool.name: tool for tool in tools}

    prompts = await client.get_prompt("expense_local_server", "expense-assistant")
    system_content = None

    for msg in prompts:
        # content is a JSON string — parse it
        parsed = json.loads(msg.content)
        for inner_msg in parsed["messages"]:
            if inner_msg["role"] == "system":
                system_content = inner_msg["content"]
                break

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key="AIzaSyDRx0EY2X56zZmf23YTnfhRBoaLJpDXf50",
        temperature=0
    )

    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_query)
    ]

    response = await llm_with_tools.ainvoke(messages)

    print("LLM Response:", response)

    # If no tool calls
    if not getattr(response, "tool_calls", None):
        return response.content

    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)

        tool_messages.append(
            ToolMessage(
                tool_call_id=selected_tool_id,
                content=json.dumps(result)
            )
        )

    final_response = await llm_with_tools.ainvoke([
        user_query,
        response,
        *tool_messages
    ])

    return final_response.content

# Streamlit UI
st.set_page_config(page_title="MCP Expense Assistant", layout="wide")

st.title("MCP Expense Assistant")

user_query = st.text_area("Enter your query:", placeholder="e.g. List expenses for March 2026")

if st.button("Run Query"):
    if not user_query.strip():
        st.warning("Please enter a query")
    else:
        with st.spinner("Processing..."):
            result = asyncio.run(run_query(user_query))
        st.success("Response:")
        st.write(result)

# Optional: chat history
if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Save to History") and user_query:
    st.session_state.history.append((user_query, result))

if st.session_state.history:
    st.subheader("History")
    for q, r in reversed(st.session_state.history):
        st.markdown(f"**Q:** {q}")
        st.markdown(f"**A:** {r}")
        st.markdown("---")
