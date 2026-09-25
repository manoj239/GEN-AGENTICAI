import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# =====================================
# LLM  (Gemini 2.5)
# =====================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

# =====================================
# MCP TOOL  (ServiceNow stub)
# =====================================

def fetch_incident_from_servicenow(incident_id: str) -> dict:
    print(f"[MCP] Fetching {incident_id} from ServiceNow")
    return {
        "short_desc": "Apache Service Down on VM-APP-01",
        "severity": "High",
        "type": "application",
        "asset": "VM-APP-01",
    }

# =====================================
# STATE  (shared across all agents)
# =====================================

class IncidentState(TypedDict):
    incident_id: str
    incident_data: dict
    diagnostic_output: str
    health_analysis: str
    rca: str
    recommended_steps: str
    approval: str
    remediation: str

# =====================================
# AGENT 1 - TRIAGE
# =====================================

def triage_agent(state: IncidentState):
    print("[1] Triage Agent")
    incident = fetch_incident_from_servicenow(state["incident_id"])
    return {"incident_data": incident}

# =====================================
# AGENT 2 - COMMAND EXECUTOR & LOG EXTRACTOR
# =====================================

def command_executor_agent(state: IncidentState):
    print("[2] Command Executor & Log Extractor")
    asset = state["incident_data"]["asset"]
    diagnostic_output = (
        f"ping {asset}: 100% packet loss | "
        f"ssh {asset}: connection refused | "
        f"logs: Apache exited with code 1"
    )
    return {"diagnostic_output": diagnostic_output}

# =====================================
# AGENT 3 - DIAGNOSTIC  (LLM)
# =====================================

def diagnostic_agent(state: IncidentState):
    print("[3] Diagnostic Agent  (LLM)")
    prompt = [
        SystemMessage(content="You analyze VM/server health from diagnostic output. Answer in 2 lines."),
        HumanMessage(content=(
            f"Incident: {state['incident_data']}\n"
            f"Diagnostic output: {state['diagnostic_output']}\n"
            "Assess current vs historical health."
        )),
    ]
    result = llm.invoke(prompt)
    return {"health_analysis": result.content}

# =====================================
# AGENT 4 - RCA / ANALYSIS  (LLM + RAG placeholder)
# =====================================

def rca_agent(state: IncidentState):
    print("[4] RCA / Analysis Agent  (LLM + RAG)")
    # In prod: retrieve top-k chunks from Runbooks/SOPs/KB/SharePoint vector store.
    runbook_context = "Runbook RB-APACHE-01: restart httpd, verify port 80, tail error_log."
    prompt = [
        SystemMessage(content="You are an SRE. Ground your RCA strictly in the runbook context."),
        HumanMessage(content=(
            f"Incident: {state['incident_data']}\n"
            f"Health: {state['health_analysis']}\n"
            f"Runbook: {runbook_context}\n"
            "Return RCA and numbered remediation steps."
        )),
    ]
    result = llm.invoke(prompt)
    return {"rca": result.content, "recommended_steps": runbook_context}

# =====================================
# CONDITIONAL EDGE 1 - need remediation?
# =====================================

def need_remediation(state: IncidentState):
    return "remediation" if state["incident_data"]["severity"] == "High" else "end"

# =====================================
# AGENT 5 - REMEDIATION  (HITL + execute)
# =====================================

def remediation_agent(state: IncidentState):
    print("[5] Remediation Agent  (HITL)")
    print(f"    RCA: {state['rca']}")
    approval = input("    Approve remediation? (yes/no): ").strip().lower()
    return {"approval": approval}

# =====================================
# CONDITIONAL EDGE 2 - approved?
# =====================================

def approval_router(state: IncidentState):
    return "execute" if state["approval"] == "yes" else "end"

def execute_remediation(state: IncidentState):
    print("[5b] Executing remediation")
    return {"remediation": f"Executed: {state['recommended_steps']}"}

# =====================================
# GRAPH
# =====================================

memory = MemorySaver()
builder = StateGraph(IncidentState)

builder.add_node("triage", triage_agent)
builder.add_node("cmd_log", command_executor_agent)
builder.add_node("diagnostic", diagnostic_agent)
builder.add_node("rca", rca_agent)
builder.add_node("remediation", remediation_agent)
builder.add_node("execute", execute_remediation)

builder.set_entry_point("triage")
builder.add_edge("triage", "cmd_log")
builder.add_edge("cmd_log", "diagnostic")
builder.add_edge("diagnostic", "rca")

builder.add_conditional_edges(
    "rca",
    need_remediation,
    {"remediation": "remediation", "end": END},
)

builder.add_conditional_edges(
    "remediation",
    approval_router,
    {"execute": "execute", "end": END},
)

builder.add_edge("execute", END)

graph = builder.compile(checkpointer=memory)

# =====================================
# EXECUTION
# =====================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "INC1001"}}
    final_state = graph.invoke({"incident_id": "INC1001"}, config=config)
    print("\n=== FINAL STATE ===")
    for k, v in final_state.items():
        print(f"{k}: {v}")


