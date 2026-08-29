from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import HumanMessage, SystemMessage

# --------------------------------
# LLM Setup
# --------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0, google_api_key="YOUR_API_KEY")

# --------------------------------
# Router Schema (Structured Output)
# --------------------------------
class Route(BaseModel):
    intent: Literal["pricing", "order_status", "refund"] = Field(
        description="Intent of the user query"
    )

router_llm = llm.with_structured_output(Route)

# --------------------------------
# Graph State
# --------------------------------
class SupportState(TypedDict):
    query: str
    intent: str
    response: str

# --------------------------------
# Support Handlers
# --------------------------------
def pricing_handler(state: SupportState):
    msg = llm.invoke(
        f"Answer this pricing-related customer question:\n{state['query']}"
    )
    return {"response": msg.content}

def order_status_handler(state: SupportState):
    msg = llm.invoke(
        f"Answer this order status-related customer question:\n{state['query']}"
    )
    return {"response": msg.content}

def refund_handler(state: SupportState):
    msg = llm.invoke(
        f"Answer this refund/return-related customer question:\n{state['query']}"
    )
    return {"response": msg.content}

# --------------------------------
# Router Node
# --------------------------------
def router_node(state: SupportState):
    decision = router_llm.invoke(
        [
            SystemMessage(
                content=(
                    "Classify the customer query into one of the following intents: "
                    "pricing, order_status, refund."
                )
            ),
            HumanMessage(content=state["query"]),
        ]
    )
    return {"intent": decision.intent}

# --------------------------------
# Routing Logic
# --------------------------------
def route_by_intent(state: SupportState):
    if state["intent"] == "pricing":
        return "pricing_handler"
    elif state["intent"] == "order_status":
        return "order_status_handler"
    elif state["intent"] == "refund":
        return "refund_handler"

# --------------------------------
# Build LangGraph Workflow
# --------------------------------
builder = StateGraph(SupportState)

builder.add_node("router", router_node)
builder.add_node("pricing_handler", pricing_handler)
builder.add_node("order_status_handler", order_status_handler)
builder.add_node("refund_handler", refund_handler)

builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    route_by_intent,
    {
        "pricing_handler": "pricing_handler",
        "order_status_handler": "order_status_handler",
        "refund_handler": "refund_handler",
    },
)

builder.add_edge("pricing_handler", END)
builder.add_edge("order_status_handler", END)
builder.add_edge("refund_handler", END)

support_graph = builder.compile()

# --------------------------------
# Invoke
# --------------------------------
result = support_graph.invoke({
    "query": "I want to return my order. What is the refund policy?"
})

print(result["response"])
