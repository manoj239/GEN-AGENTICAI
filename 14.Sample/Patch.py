import os
from typing import TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# =====================================
# LLM  (Gemini 2.5)
# =====================================

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0,google_api_key=os.getenv("GOOGLE_API_KEY"),)
# =====================================
# MCP TOOLS  (stubs)
# =====================================

def get_patch_info() -> dict:
    print("[MCP] get_patch_info()")
    return {"missing_patches": 15, "critical": True, "os": "RHEL8"}

def retrieve_runbook(patch_type: str) -> str:
    print(f"[MCP/RAG] retrieve_runbook({patch_type})")
    return (
        "RB-PATCH-01:\n"
        "1. yum update --security -y\n"
        "2. systemctl restart critical-services\n"
        "3. verify service health on port 443"
    )

# =====================================
# STATE  (shared across all agents)
# =====================================

class PatchState(TypedDict):
    patch_data: dict
    risk_level: str
    risk_reason: str
    runbook: str
    approval: str
    remediation: str
    validation: str
    compliance_report: str

# =====================================
# STRUCTURED OUTPUT  (Pydantic)
# =====================================

class RiskDecision(BaseModel):
    risk_level: Literal["HIGH", "LOW"] = Field(description="HIGH if any critical patch, else LOW")
    reason: str = Field(description="One-line justification")

# =====================================
# AGENT 1 - SUPERVISOR
# =====================================

def supervisor_agent(state: PatchState):
    print("[1] Supervisor Agent")
    return state

# =====================================
# AGENT 2 - PATCH ASSESSMENT
# =====================================

def patch_assessment_agent(state: PatchState):
    print("[2] Patch Assessment Agent")
    return {"patch_data": get_patch_info()}

# =====================================
# AGENT 3 - RISK ANALYSIS  (LLM + structured output)
# =====================================

def risk_analysis_agent(state: PatchState):
    print("[3] Risk Analysis Agent  (LLM)")
    structured_llm = llm.with_structured_output(RiskDecision)
    decision: RiskDecision = structured_llm.invoke([
        SystemMessage(content="Classify patch risk. HIGH if critical=True."),
        HumanMessage(content=f"Patch data: {state['patch_data']}"),
    ])
    return {"risk_level": decision.risk_level, "risk_reason": decision.reason}

# =====================================
# AGENT 4 - RUNBOOK  (RAG)
# =====================================

def runbook_agent(state: PatchState):
    print("[4] Runbook Agent  (RAG)")
    runbook = retrieve_runbook(state["patch_data"]["os"])
    return {"runbook": runbook}

# =====================================
# AGENT 5 - HUMAN APPROVAL  (HITL)
# =====================================

def approval_agent(state: PatchState):
    print("[5] Human Approval Agent")
    print(f"    Risk: {state['risk_level']} — {state['risk_reason']}")
    print(f"    Runbook:\n{state['runbook']}")
    approval = input("    Approve patch? (yes/no): ").strip().lower()
    return {"approval": approval}

# =====================================
# CONDITIONAL EDGE - approved?
# =====================================

def approval_router(state: PatchState):
    return "remediation" if state["approval"] == "yes" else "end"

# =====================================
# AGENT 6 - REMEDIATION
# =====================================

def remediation_agent(state: PatchState):
    print("[6] Remediation Agent")
    return {"remediation": "Patches installed successfully per runbook"}

# =====================================
# AGENT 7 - VALIDATION
# =====================================

def validation_agent(state: PatchState):
    print("[7] Validation Agent")
    return {"validation": "Services Healthy"}

# =====================================
# AGENT 8 - COMPLIANCE  (LLM)
# =====================================

def compliance_agent(state: PatchState):
    print("[8] Compliance Agent  (LLM)")
    result = llm.invoke([
        SystemMessage(content="You write concise 3-line audit reports for patch runs."),
        HumanMessage(content=(
            f"Patch: {state['patch_data']} | Risk: {state['risk_level']} | "
            f"Approval: {state['approval']} | Remediation: {state['remediation']} | "
            f"Validation: {state['validation']}"
        )),
    ])
    return {"compliance_report": result.content}

# =====================================
# GRAPH
# =====================================

memory = MemorySaver()
builder = StateGraph(PatchState)

builder.add_node("supervisor", supervisor_agent)
builder.add_node("assessment", patch_assessment_agent)
builder.add_node("risk", risk_analysis_agent)
builder.add_node("runbook", runbook_agent)
builder.add_node("approval", approval_agent)
builder.add_node("remediation", remediation_agent)
builder.add_node("validation", validation_agent)
builder.add_node("compliance", compliance_agent)

builder.set_entry_point("supervisor")
builder.add_edge("supervisor", "assessment")
builder.add_edge("assessment", "risk")
builder.add_edge("risk", "runbook")
builder.add_edge("runbook", "approval")

builder.add_conditional_edges(
    "approval",
    approval_router,
    {"remediation": "remediation", "end": END},
)

builder.add_edge("remediation", "validation")
builder.add_edge("validation", "compliance")
builder.add_edge("compliance", END)

graph = builder.compile(checkpointer=memory)

# =====================================
# EXECUTION
# =====================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "PATCH-2026-001"}}
    final_state = graph.invoke({}, config=config)
    print("\n=== FINAL STATE ===")
    for k, v in final_state.items():
        print(f"{k}: {v}")
