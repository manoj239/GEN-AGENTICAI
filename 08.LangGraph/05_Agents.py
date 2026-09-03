    # ===============================
    # Imports
    # ===============================
    from typing import Literal

    from langchain.tools import tool
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.messages import SystemMessage, HumanMessage, ToolMessage

    from langgraph.graph import StateGraph, START, END, MessagesState
    from IPython.display import Image, display


    # ===============================
    # Gemini 2.5 Flash LLM
    # ===============================
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0, google_api_key="YOUR_API_KEY")


    # ===============================
    # Define Tools
    # ===============================
    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply a and b."""
        return a * b


    @tool
    def add(a: int, b: int) -> int:
        """Add a and b."""
        return a + b


    @tool
    def divide(a: int, b: int) -> float:
        """Divide a and b."""
        return a / b


    tools = [add, multiply, divide]
    tools_by_name = {tool.name: tool for tool in tools}

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)


    # ===============================
    # Nodes
    # ===============================
    def llm_call(state: MessagesState):
        """LLM decides whether to call a tool"""

        response = llm_with_tools.invoke(
            [SystemMessage(content="You are a helpful assistant that performs arithmetic.")]
            + state["messages"]
        )

        return {"messages": [response]}


    def tool_node(state: MessagesState):
        """Execute tool calls"""

        results = []
        last_message = state["messages"][-1]

        for tool_call in last_message.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])

            results.append(
                ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_call["id"]
                )
            )

        return {"messages": results}


    # ===============================
    # Routing Logic
    # ===============================
    def should_continue(state: MessagesState) -> Literal["tool_node", END]:
        last_message = state["messages"][-1]

        if last_message.tool_calls:
            return "tool_node"

        return END


    # ===============================
    # Build Agent Graph
    # ===============================
    builder = StateGraph(MessagesState)

    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END]
    )
    builder.add_edge("tool_node", "llm_call")

    agent = builder.compile()


    # ===============================
    # Visualize Agent
    # ===============================
    display(Image(agent.get_graph(xray=True).draw_mermaid_png()))


    # ===============================
    # Invoke Agent
    # ===============================
    messages = [HumanMessage(content="Add 3 and 4 and multiply this with 5 and divide it with 3")]
    result = agent.invoke({"messages": messages})

    for msg in result["messages"]:
        msg.pretty_print()
