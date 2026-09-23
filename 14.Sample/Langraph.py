from typing import TypedDict
from huggingface_hub import User
from langgraph.graph import (StateGraph, END)
from langgraph.checkpoint.memory import (MemorySaver)

# =====================================
# MCP TOOL
# =====================================

def fetch_incident_from_servicenow(incident_id:str):

    print(f"Fetching {incident_id} from ServiceNow MCP")

    return {

        "short_desc": "Apache Service Down",

        "severity": "High"
    }

# =====================================
# STATE
# =====================================

class IncidentState(TypedDict):
    incident_id: str
    incident_data: dict
    analysis: str
    approval: str
    remediation: str
# =====================================
# NODE 1
# ORCHESTRATOR
# =====================================

def orchestrator(state:IncidentState):
    print("Orchestrator Started")
    return state

# =====================================
# NODE 2
# MCP TOOL CALL
# =====================================

def intake_agent(state:IncidentState):
    incident = fetch_incident_from_servicenow(
        state["incident_id"]
    )
    return {"incident_data":  incident}

# =====================================
# NODE 3
# ANALYSIS AGENT
# =====================================

def analysis_agent(state:IncidentState):
    analysis = f"""
    RCA:
    Service outage identified
    """
    return { "analysis":  analysis}

# =====================================
# ROUTER
# CONDITIONAL EDGE
# =====================================

def need_remediation( state:IncidentState):
    severity = state[ "incident_data"]["severity"]
    if severity == "High":
        return "approval"
    return "end"

# =====================================
# NODE 4
# HUMAN IN LOOP
# =====================================

def approval_agent(state:IncidentState):

    approval = input("Approve remediation? (yes/no): " )

    return { "approval":  approval}

# =====================================
# ROUTER
# =====================================

def approval_router( state:IncidentState):
    if state["approval"] == "yes":
        return "remediation"
    return "end"

# =====================================
# NODE 5
# REMEDIATION AGENT
# =====================================

def remediation_agent(state:IncidentState):
    action = """
    Restart Apache Service
    """
    return { "remediation": action}

# =====================================
# CHECKPOINTER
# MEMORY
# =====================================

memory = MemorySaver()

# =====================================
# GRAPH
# =====================================

builder = StateGraph(IncidentState)
builder.add_node("orchestrator",orchestrator)
builder.add_node("intake",intake_agent)
builder.add_node("analysis",analysis_agent)
builder.add_node("approval",approval_agent)
builder.add_node("remediation",remediation_agent)
# =====================================
# EDGES
# =====================================

builder.set_entry_point("orchestrator")

builder.add_edge( "orchestrator",  "intake")

builder.add_edge( "intake", "analysis")

builder.add_conditional_edges(
    "analysis",
    need_remediation,

    {

        "approval":"approval",

        "end":END
    }
)

builder.add_conditional_edges(

    "approval",

    approval_router,

    {

        "remediation":"remediation",

        "end":END
    }
)

builder.add_edge( "remediation", END)

graph = builder.compile(checkpointer=memory)

# =====================================
# EXECUTION
# =====================================

graph.invoke( {

        "incident_id":
            "INC1001"
    }
)

I designed the workflow using LangGraph's StateGraph. The state object carried incident 
information across agents. The orchestrator initiated the workflow. The intake agent 
invoked a ServiceNow MCP tool to retrieve incident details. The analysis agent performed 
. Conditional routing determined whether remediation was required. For high-severity incidents, 
the workflow moved to a Human-in-the-Loop approval step. After approval, the remediation agent 
executed corrective actions. I used LangGraph's MemorySaver as a checkpointer to persist workflow state and 
support resumability. This architecture demonstrates agent collaboration, orchestration, memory, 
tool integration, and enterprise automation patterns.

# =====================================================================
# CONCEPT MAPPING TABLE
# =====================================================================
# +--------------------------+----------------------------------------------+
# | Concept                  | Implementation                               |
# +--------------------------+----------------------------------------------+
# | State Management         | IncidentState (TypedDict)                    |
# | Nodes                    | Orchestrator, Intake, Analysis, Approval,    |
# |                          | Remediation                                  |
# | Edges                    | add_edge() / add_conditional_edges()         |
# | Agent Collaboration      | Analysis -> Approval -> Remediation          |
# | Tool Calling             | ServiceNow MCP Tool                          |
# | MCP                      | fetch_incident_from_servicenow()             |
# | Human Approval           | approval_agent()                             |
# | Persistence              | MemorySaver()                                |
# | Workflow Orchestration   | Orchestrator coordinates flow                |
# | Memory Checkpointer      | MemorySaver()                                |
# +--------------------------+----------------------------------------------+



#Architecture
#
#                        +------------------+
#                        |       User       |
#                        +------------------+
#                                 |
#                                 v
#                        +--------------------+
#                        | Orchestrator Agent |
#                        +--------------------+
#                                 |
#                                 v
#                        +-----------------------------+
#                        | Intake Agent (MCP Tool)     |
#                        | fetch_incident_from_service |
#                        +-----------------------------+
#                                 |
#                                 v
#                        +------------------+
#                        |  Analysis Agent  |
#                        +------------------+
#                                 |
#                                 v
#                        +---------------------+
#                        |  Need Remediation?  |
#                        +---------------------+
#                             |          |
#                          NO |          | YES
#                             v          v
#                        +-------+   +------------------+
#                        |  END  |   |  Human Approval  |
#                        +-------+   +------------------+
#                                             |
#                                             v
#                                    +----------------+
#                                    |   Approved?    |
#                                    +----------------+
#                                       |        |
#                                    YES|        |NO
#                                       v        v
#                            +--------------------+  +-------+
#                            | Remediation Agent  |  |  END  |
#                            +--------------------+  +-------+
#                                     |
#                                     v
#                                 +-------+
#                                 |  END  |
#                                 +-------+