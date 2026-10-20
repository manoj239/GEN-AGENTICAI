import os
import time
import random
import functools
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import TypedDict, Optional, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# =====================================
# RESILIENCE CONFIG
# =====================================

MAX_RETRIES = 3                 # attempts per tool / LLM call
RETRY_BASE_DELAY = 1.0          # seconds, exponential backoff base
RETRY_MAX_DELAY = 8.0           # cap per-attempt sleep
TOOL_TIMEOUT = 15               # seconds per MCP / diagnostic tool call
LLM_TIMEOUT = 45                # seconds per LLM call
HITL_TIMEOUT = 120              # seconds to wait for human approval
MAX_TOOL_CALLS = 12             # hard budget across the whole run
RECURSION_LIMIT = 25            # LangGraph super-step limit (loop guard)


class BudgetExceeded(Exception):
    """Raised when the run exceeds its tool-call budget."""


class NodeFailure(Exception):
    """Raised when a node exhausts its retries."""


# =====================================
# RETRY + TIMEOUT WRAPPER
# =====================================

_executor = ThreadPoolExecutor(max_workers=4)


def resilient(timeout: int, retries: int = MAX_RETRIES, retry_on=(Exception,)):
    """Run a callable with a hard timeout and bounded exponential-backoff retries."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error: Optional[BaseException] = None
            for attempt in range(1, retries + 1):
                try:
                    return _executor.submit(fn, *args, **kwargs).result(timeout=timeout)
                except FutureTimeout:
                    last_error = TimeoutError(f"{fn.__name__} timed out after {timeout}s")
                except retry_on as exc:
                    last_error = exc
                if attempt < retries:
                    delay = min(RETRY_BASE_DELAY * 2 ** (attempt - 1), RETRY_MAX_DELAY)
                    delay += random.uniform(0, 0.3)  # jitter avoids synchronized retry storms
                    print(f"    [retry {attempt}/{retries}] {fn.__name__}: {last_error} -> sleep {delay:.1f}s")
                    time.sleep(delay)
            raise NodeFailure(f"{fn.__name__} failed after {retries} attempts: {last_error}")

        return wrapper

    return decorator


def guarded_node(name: str):
    """Record node failures in state and stop the run instead of crashing the graph."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state: "IncidentState"):
            if state.get("status") in ("failed", "aborted"):
                return {}
            try:
                return fn(state)
            except (NodeFailure, BudgetExceeded, KeyError, ValueError) as exc:
                print(f"    [FAILED] {name}: {exc}")
                return {
                    "status": "failed",
                    "failed_node": name,
                    "errors": state.get("errors", []) + [f"{name}: {exc}"],
                }

        return wrapper

    return decorator


# =====================================
# LLM  (Gemini 2.5)
# =====================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_retries=0,  # retry policy is owned by the @resilient wrapper
    timeout=LLM_TIMEOUT,
)


@resilient(timeout=LLM_TIMEOUT)
def call_llm(prompt) -> str:
    content = (llm.invoke(prompt).content or "").strip()
    if not content:
        raise ValueError("empty LLM response")
    return content


# =====================================
# TOOL-CALL BUDGET
# =====================================

def charge_tool_call(state: "IncidentState", tool_name: str) -> int:
    used = state.get("tool_calls", 0) + 1
    if used > MAX_TOOL_CALLS:
        raise BudgetExceeded(f"tool-call budget {MAX_TOOL_CALLS} exhausted at '{tool_name}'")
    return used


# =====================================
# MCP TOOLS  (ServiceNow + diagnostics stubs)
# =====================================

@resilient(timeout=TOOL_TIMEOUT)
def fetch_incident_from_servicenow(incident_id: str) -> dict:
    print(f"[MCP] Fetching {incident_id} from ServiceNow")
    incident = {
        "short_desc": "Apache Service Down on VM-APP-01",
        "severity": "High",
        "type": "application",
        "asset": "VM-APP-01",
    }
    missing = {"severity", "asset"} - incident.keys()
    if missing:
        raise ValueError(f"incident {incident_id} missing fields: {missing}")
    return incident


@resilient(timeout=TOOL_TIMEOUT)
def run_diagnostics(asset: str) -> str:
    return (
        f"ping {asset}: 100% packet loss | "
        f"ssh {asset}: connection refused | "
        f"logs: Apache exited with code 1"
    )


# =====================================
# STATE  (shared across all agents)
# =====================================

class IncidentState(TypedDict, total=False):
    incident_id: str
    incident_data: dict
    diagnostic_output: str
    health_analysis: str
    rca: str
    recommended_steps: str
    approval: str
    remediation: str
    # resilience bookkeeping
    status: str              # running | completed | failed | aborted
    failed_node: str
    errors: List[str]
    tool_calls: int


# =====================================
# AGENT 1 - TRIAGE
# =====================================

@guarded_node("triage")
def triage_agent(state: IncidentState):
    print("[1] Triage Agent")
    used = charge_tool_call(state, "servicenow.fetch_incident")
    incident = fetch_incident_from_servicenow(state["incident_id"])
    return {"incident_data": incident, "tool_calls": used, "status": "running"}

# =====================================
# AGENT 2 - COMMAND EXECUTOR & LOG EXTRACTOR
# =====================================

@guarded_node("cmd_log")
def command_executor_agent(state: IncidentState):
    print("[2] Command Executor & Log Extractor")
    asset = state["incident_data"]["asset"]
    used = charge_tool_call(state, "diagnostics.run")
    return {"diagnostic_output": run_diagnostics(asset), "tool_calls": used}

# =====================================
# AGENT 3 - DIAGNOSTIC  (LLM)
# =====================================

@guarded_node("diagnostic")
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
    return {"health_analysis": call_llm(prompt)}

# =====================================
# AGENT 4 - RCA / ANALYSIS  (LLM + RAG placeholder)
# =====================================

@guarded_node("rca")
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
    return {"rca": call_llm(prompt), "recommended_steps": runbook_context}

# =====================================
# CONDITIONAL EDGE 1 - need remediation?
# =====================================

def need_remediation(state: IncidentState):
    if state.get("status") == "failed" or not state.get("rca"):
        return "fail"
    return "remediation" if state["incident_data"]["severity"] == "High" else "end"

# =====================================
# AGENT 5 - REMEDIATION  (HITL + execute, timeout-bounded)
# =====================================

def _ask_human() -> str:
    return input("    Approve remediation? (yes/no): ").strip().lower()


@guarded_node("remediation")
def remediation_agent(state: IncidentState):
    print("[5] Remediation Agent  (HITL)")
    print(f"    RCA: {state['rca']}")
    try:
        approval = _executor.submit(_ask_human).result(timeout=HITL_TIMEOUT)
    except FutureTimeout:
        # fail-safe: no answer in time means no change is executed
        print(f"    [HITL] no response in {HITL_TIMEOUT}s -> auto-deny")
        return {
            "approval": "timeout",
            "status": "aborted",
            "errors": state.get("errors", []) + ["remediation: HITL approval timed out"],
        }
    return {"approval": approval}

# =====================================
# CONDITIONAL EDGE 2 - approved?
# =====================================

def approval_router(state: IncidentState):
    if state.get("status") in ("failed", "aborted"):
        return "fail"
    return "execute" if state.get("approval") == "yes" else "end"


@resilient(timeout=TOOL_TIMEOUT, retries=2)
def _apply_remediation(steps: str) -> str:
    return f"Executed: {steps}"


@guarded_node("execute")
def execute_remediation(state: IncidentState):
    print("[5b] Executing remediation")
    used = charge_tool_call(state, "change.execute")
    return {
        "remediation": _apply_remediation(state["recommended_steps"]),
        "tool_calls": used,
        "status": "completed",
    }

# =====================================
# TERMINAL FAILURE HANDLER
# =====================================

def failure_handler(state: IncidentState):
    print("[X] Failure handler - escalating to on-call")
    return {
        "status": state.get("status", "failed"),
        "remediation": "NOT EXECUTED - escalated to human on-call",
    }

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
builder.add_node("failure", failure_handler)

builder.set_entry_point("triage")


def continue_or_fail(next_node: str):
    """Short-circuit the linear path to the failure handler once a node has failed."""
    def router(state: IncidentState):
        return "fail" if state.get("status") == "failed" else next_node
    return router


builder.add_conditional_edges("triage", continue_or_fail("cmd_log"),
                              {"cmd_log": "cmd_log", "fail": "failure"})
builder.add_conditional_edges("cmd_log", continue_or_fail("diagnostic"),
                              {"diagnostic": "diagnostic", "fail": "failure"})
builder.add_conditional_edges("diagnostic", continue_or_fail("rca"),
                              {"rca": "rca", "fail": "failure"})

builder.add_conditional_edges(
    "rca",
    need_remediation,
    {"remediation": "remediation", "end": END, "fail": "failure"},
)

builder.add_conditional_edges(
    "remediation",
    approval_router,
    {"execute": "execute", "end": END, "fail": "failure"},
)

builder.add_edge("execute", END)
builder.add_edge("failure", END)

graph = builder.compile(checkpointer=memory)

# =====================================
# EXECUTION
# =====================================

if __name__ == "__main__":
    config = {
        "configurable": {"thread_id": "INC1001"},
        "recursion_limit": RECURSION_LIMIT,   # terminates runaway loops
    }
    initial_state = {"incident_id": "INC1001", "status": "running", "errors": [], "tool_calls": 0}
    try:
        final_state = graph.invoke(initial_state, config=config)
    except Exception as exc:
        print(f"\n=== RUN ABORTED: {type(exc).__name__}: {exc} ===")
        final_state = graph.get_state(config).values  # fall back to last checkpoint

    print("\n=== FINAL STATE ===")
    for k, v in final_state.items():
        print(f"{k}: {v}")


