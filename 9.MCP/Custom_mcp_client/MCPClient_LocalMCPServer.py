import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage
import json
# pip install langchain langchain-mcp-adapters langchain-google-genai python-dotenv
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

async def main():
    
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    named_tools = {tool.name: tool for tool in tools}

    print("Available tools:", named_tools.keys())

    # Gemini 2.5 Flash LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key="AIzaSyDRx0EY2X56zZmf23YTnfhRBoaLJpDXf50",
        temperature=0
    )

    llm_with_tools = llm.bind_tools(tools)

    prompt = "Could you please list all expenses for the month of March 2026 and summarize the total amount spent in each category?"
    response = await llm_with_tools.ainvoke(prompt)

    if not getattr(response, "tool_calls", None):
        print("\nLLM Reply:", response.content)
        return

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

    final_response = await llm_with_tools.ainvoke([prompt, response, *tool_messages])
    print(f"Final response: {final_response.content}")


if __name__ == '__main__':
    asyncio.run(main())