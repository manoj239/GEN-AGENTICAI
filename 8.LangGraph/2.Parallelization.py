from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

# LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0, google_api_key="YOUR_API_KEY")

# ----------------------------
# Graph State
# ----------------------------
class ReviewState(TypedDict):
    document: str
    summary: str
    risks: str
    compliance: str
    final_report: str

# ----------------------------
# Parallel Nodes
# ----------------------------
def summarize_doc(state: ReviewState):
    msg = llm.invoke(
        f"Summarize the following document:\n{state['document']}"
    )
    return {"summary": msg.content}

def extract_risks(state: ReviewState):
    msg = llm.invoke(
        f"Identify potential risks in the following document:\n{state['document']}"
    )
    return {"risks": msg.content}

def compliance_check(state: ReviewState):
    msg = llm.invoke(
        f"Check this document for compliance or policy issues:\n{state['document']}"
    )
    return {"compliance": msg.content}

# ----------------------------
# Aggregator Node
# ----------------------------
def aggregate_results(state: ReviewState):
    report = f"""
DOCUMENT REVIEW REPORT

SUMMARY:
{state['summary']}

RISKS:
{state['risks']}

COMPLIANCE ISSUES:
{state['compliance']}
"""
    return {"final_report": report}

# ----------------------------
# Build Parallel Graph
# ----------------------------
builder = StateGraph(ReviewState)

builder.add_node("summarize", summarize_doc)
builder.add_node("risks", extract_risks)
builder.add_node("compliance", compliance_check)
builder.add_node("aggregate", aggregate_results)

# Parallel execution from START
builder.add_edge(START, "summarize")
builder.add_edge(START, "risks")
builder.add_edge(START, "compliance")

# Join at aggregator
builder.add_edge("summarize", "aggregate")
builder.add_edge("risks", "aggregate")
builder.add_edge("compliance", "aggregate")

builder.add_edge("aggregate", END)

graph = builder.compile()

# ----------------------------
# Invoke
# ----------------------------
result = graph.invoke({
    "document": "This contract allows data sharing with third parties for analytics purposes."
})

print(result["final_report"])
