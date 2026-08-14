from langgraph.graph import StateGraph, MessagesState, START, END
graph = StateGraph(MessagesState)
def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}

def node2(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "Node2"}]}

def node3(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "Node3"}]}
graph.add_node(mock_llm)
graph.add_node(node2)
graph.add_node(node3)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", "node2")
graph.add_edge("mock_llm", "node3")
graph.add_edge("node2", END)
graph.add_edge("node3", END)
graph = graph.compile()
graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})