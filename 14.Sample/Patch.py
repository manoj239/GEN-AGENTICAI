from typing import TypedDict
from langgraph.graph import (StateGraph, END)
from langgraph.checkpoint.memory import (MemorySaver)

# ====================================
# MCP TOOL
# ====================================

def get_patch_info():
    return {
        "missing_patches": 15,
        "critical": True
    }

# ====================================
# STATE
# ====================================

class PatchState(TypedDict):
    patch_data: dict
    risk_level: str
    runbook: str
    approval: str
    remediation: str
    validation: str

# ====================================
# NODE 1
# SUPERVISOR
# ====================================

def supervisor_agent(state: PatchState):
    print("Supervisor Monitoring Workflow")
    return state

# ====================================
# NODE 2
# PATCH ASSESSMENT
# ====================================

def patch_assessment_agent(state: PatchState):
    patch_info = get_patch_info()
    return {"patch_data": patch_info}

# ====================================
# NODE 3
# RISK ANALYSIS
# ====================================

def risk_analysis_agent(state: PatchState):
    critical = state["patch_data"]["critical"]
    risk = "HIGH" if critical else "LOW"
    return {"risk_level": risk}

# ====================================
# MCP RUNBOOK TOOL
# ====================================

def retrieve_runbook():
    return """
    Apply approved security patches
    Restart services if required
    Validate service health
    """

# ====================================
# NODE 4
# RAG AGENT
# ====================================

def runbook_agent(state: PatchState):
    runbook = retrieve_runbook()
    return {"runbook": runbook}

# ====================================
# NODE 5
# HUMAN APPROVAL
# ====================================

def approval_agent(state: PatchState):
    approval = input("Approve patch? (yes/no): ")
    return {"approval": approval}

# ====================================
# ROUTER
# ====================================

def approval_router(state: PatchState):
    if state["approval"] == "yes":
        return "remediation"
    return "end"

# ====================================
# NODE 6
# REMEDIATION
# ====================================

def remediation_agent(state: PatchState):
    return {"remediation": "Patches installed successfully"}

# ====================================
# NODE 7
# VALIDATION
# ====================================

def validation_agent(state: PatchState):
    return {"validation": "Services Healthy"}

# ====================================
# NODE 8
# COMPLIANCE REPORT
# ====================================

def compliance_agent(state: PatchState):
    print("Compliance report generated")
    return state

# ====================================
# CHECKPOINTER
# MEMORY
# ====================================

memory = MemorySaver()

# ====================================
# GRAPH
# ====================================

builder = StateGraph(PatchState)
builder.add_node("supervisor", supervisor_agent)
builder.add_node("assessment", patch_assessment_agent)
builder.add_node("risk", risk_analysis_agent)
builder.add_node("runbook", runbook_agent)
builder.add_node("approval", approval_agent)
builder.add_node("remediation", remediation_agent)
builder.add_node("validation", validation_agent)
builder.add_node("compliance", compliance_agent)

# ====================================
# EDGES
# ====================================

builder.set_entry_point("supervisor")

builder.add_edge("supervisor", "assessment")
builder.add_edge("assessment", "risk")
builder.add_edge("risk", "runbook")
builder.add_edge("runbook", "approval")

builder.add_conditional_edges(
    "approval",
    approval_router,
    {
        "remediation": "remediation",
        "end": END
    }
)

builder.add_edge("remediation", "validation")
builder.add_edge("validation", "compliance")
builder.add_edge("compliance", END)

graph = builder.compile(checkpointer=memory)

# ====================================
# EXECUTION
# ====================================

graph.invoke({})

# I implemented the patching workflow using LangGraph's Supervisor pattern. The Supervisor Agent
# controlled workflow execution while specialized agents handled patch assessment, risk analysis,
# runbook retrieval, remediation, validation, and compliance reporting. MCP tools were used to
# retrieve patch information and operational runbooks. State was maintained using a shared LangGraph
# state object and persisted through a checkpointer. Human-in-the-Loop approval was incorporated
# before remediation actions, and conditional routing determined whether the workflow should
# proceed with patch execution. This design provided governance, safety, auditability, and
# enterprise-scale automation for patch management.

# =====================================================================
# CONCEPT MAPPING TABLE
# =====================================================================
# +--------------------------+----------------------------------------------+
# | Concept                  | Implementation                               |
# +--------------------------+----------------------------------------------+
# | State Management         | PatchState (TypedDict)                       |
# | Supervisor Pattern       | supervisor_agent()                           |
# | Nodes                    | Supervisor, Assessment, Risk, Runbook,       |
# |                          | Approval, Remediation, Validation,           |
# |                          | Compliance                                   |
# | Edges                    | add_edge() / add_conditional_edges()         |
# | Agent Collaboration      | Assessment -> Risk -> Runbook -> Approval    |
# | Tool Calling             | get_patch_info(), retrieve_runbook()         |
# | MCP                      | Patch Info + Runbook MCP tools               |
# | RAG                      | runbook_agent() (Runbooks / SOPs)            |
# | Human Approval           | approval_agent()                             |
# | Conditional Routing      | approval_router()                            |
# | Persistence              | MemorySaver()                                |
# | Workflow Orchestration   | Supervisor coordinates flow                  |
# | Memory Checkpointer      | MemorySaver()                                |
# +--------------------------+----------------------------------------------+

# Architecture
#
#                        +------------------+
#                        |       User       |
#                        +------------------+
#                                 |
#                                 v
#                        +--------------------+
#                        |  Supervisor Agent  |
#                        +--------------------+
#                                 |
#                                 v
#                        +--------------------------+
#                        |  Patch Assessment Agent  |
#                        |    (MCP: patch info)     |
#                        +--------------------------+
#                                 |
#                                 v
#                        +----------------------+
#                        | Risk Analysis Agent  |
#                        +----------------------+
#                                 |
#                                 v
#                        +----------------------+
#                        |      RAG Agent       |
#                        |  (Runbooks / SOPs)   |
#                        +----------------------+
#                                 |
#                                 v
#                        +----------------------+
#                        |   Approval Agent     |
#                        |  (Human in Loop)     |
#                        +----------------------+
#                                 |
#                                 v
#                        +----------------------+
#                        |     Approved?        |
#                        +----------------------+
#                             |          |
#                          YES|          |NO
#                             v          v
#                    +--------------------+  +-------+
#                    | Remediation Agent  |  |  END  |
#                    +--------------------+  +-------+
#                             |
#                             v
#                    +--------------------+
#                    |  Validation Agent  |
#                    +--------------------+
#                             |
#                             v
#                    +--------------------------+
#                    | Compliance Report Agent  |
#                    +--------------------------+
#                             |
#                             v
#                         +-------+
#                         |  END  |
#                         +-------+