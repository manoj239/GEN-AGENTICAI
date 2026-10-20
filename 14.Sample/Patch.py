import os
import time
import random
import hashlib
import functools
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import TypedDict, Literal, Optional, List, Dict

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# =====================================
# RESILIENCE CONFIG
# =====================================

MAX_RETRIES = 3                  # attempts per tool / LLM call
RETRY_BASE_DELAY = 1.0           # seconds, exponential backoff base
RETRY_MAX_DELAY = 8.0            # cap per-attempt sleep
TOOL_TIMEOUT = 15                # seconds per MCP tool call
LLM_TIMEOUT = 45                 # seconds per LLM call
HITL_TIMEOUT = 300               # seconds to wait for approval, then auto-deny
MAX_TOOL_CALLS = 20              # hard tool-call budget for the whole run
MAX_NODE_ATTEMPTS = 2            # how often one node may execute in a run
MAX_REMEDIATION_ATTEMPTS = 2     # patch install attempts before rollback
RECURSION_LIMIT = 30             # LangGraph super-step limit (loop guard)


class BudgetExceeded(Exception):
    """Raised when the run exceeds its tool-call or node-attempt budget."""


class NodeFailure(Exception):
    """Raised when a tool or LLM call exhausts its retries."""


_executor = ThreadPoolExecutor(max_workers=4)


# =====================================
# RETRY + TIMEOUT WRAPPER
# =====================================

def resilient(timeout: int, retries: int = MAX_RETRIES):
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
                except Exception as exc:
                    last_error = exc
                if attempt < retries:
                    delay = min(RETRY_BASE_DELAY * 2 ** (attempt - 1), RETRY_MAX_DELAY)
                    delay += random.uniform(0, 0.3)  # jitter avoids synchronized retry storms
                    print(f"    [retry {attempt}/{retries}] {fn.__name__}: {last_error} -> sleep {delay:.1f}s")
                    time.sleep(delay)
            raise NodeFailure(f"{fn.__name__} failed after {retries} attempts: {last_error}")

        return wrapper

    return decorator


# =====================================
# NODE GUARD  (idempotency + attempt cap + error capture)
# =====================================

def guarded_node(name: str, produces: Optional[str] = None):
    """Skip already-satisfied nodes, cap re-executions, and turn failures into state."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state: "PatchState"):
            if state.get("status") in ("failed", "aborted"):
                return {}

            # idempotency: on a resumed/replayed run the node's output already exists
            if produces and state.get(produces):
                print(f"    [skip] {name}: '{produces}' already in state")
                return {}

            attempts = dict(state.get("node_attempts", {}))
            attempts[name] = attempts.get(name, 0) + 1
            try:
                if attempts[name] > MAX_NODE_ATTEMPTS:
                    raise BudgetExceeded(f"node '{name}' exceeded {MAX_NODE_ATTEMPTS} attempts")
                update = fn(state)
            except (NodeFailure, BudgetExceeded, KeyError, ValueError) as exc:
                print(f"    [FAILED] {name}: {exc}")
                return {
                    "status": "failed",
                    "failed_node": name,
                    "errors": state.get("errors", []) + [f"{name}: {exc}"],
                    "node_attempts": attempts,
                }
            return {**update, "node_attempts": attempts}

        return wrapper

    return decorator


def charge_tool_call(state: "PatchState", tool_name: str) -> int:
    used = state.get("tool_calls", 0) + 1
    if used > MAX_TOOL_CALLS:
        raise BudgetExceeded(f"tool-call budget {MAX_TOOL_CALLS} exhausted at '{tool_name}'")
    return used


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
# MCP TOOLS  (stubs)
# =====================================

@resilient(timeout=TOOL_TIMEOUT)
def get_patch_info() -> dict:
    print("[MCP] get_patch_info()")
    info = {"missing_patches": 15, "critical": True, "os": "RHEL8"}
    missing = {"missing_patches", "critical", "os"} - info.keys()
    if missing:
        raise ValueError(f"patch scan returned incomplete data, missing: {missing}")
    return info


@resilient(timeout=TOOL_TIMEOUT)
def retrieve_runbook(patch_type: str) -> str:
    print(f"[MCP/RAG] retrieve_runbook({patch_type})")
    runbook = (
        "RB-PATCH-01:\n"
        "1. yum update --security -y\n"
        "2. systemctl restart critical-services\n"
        "3. verify service health on port 443"
    )
    if not runbook.strip():
        raise ValueError(f"no runbook found for '{patch_type}'")  # fail closed, never patch unguided
    return runbook


@resilient(timeout=TOOL_TIMEOUT, retries=1)
def apply_patches(runbook: str, idempotency_key: str) -> str:
    """Change action: retried only via the explicit remediation loop, never blindly."""
    print(f"[MCP] apply_patches(key={idempotency_key})")
    return "Patches installed successfully per runbook"


@resilient(timeout=TOOL_TIMEOUT)
def check_service_health() -> str:
    print("[MCP] check_service_health()")
    return "Services Healthy"


@resilient(timeout=TOOL_TIMEOUT, retries=1)
def rollback_patches(idempotency_key: str) -> str:
    print(f"[MCP] rollback_patches(key={idempotency_key})")
    return "Rolled back to pre-patch snapshot"


# =====================================
# STATE  (shared across all agents)
# =====================================

class PatchState(TypedDict, total=False):
    patch_data: dict
    risk_level: str
    risk_reason: str
    runbook: str
    approval: str
    remediation: str
    validation: str
    compliance_report: str
    # resilience bookkeeping
    status: str                     # running | completed | failed | aborted | rolled_back
    failed_node: str
    errors: List[str]
    tool_calls: int
    node_attempts: Dict[str, int]
    remediation_attempts: int
    idempotency_key: str

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
    return {
        "status": "running",
        "errors": state.get("errors", []),
        "tool_calls": state.get("tool_calls", 0),
        "remediation_attempts": state.get("remediation_attempts", 0),
        "idempotency_key": state.get("idempotency_key")
        or hashlib.sha256(str(state.get("patch_data", "PATCH-RUN")).encode()).hexdigest()[:12],
    }

# =====================================
# AGENT 2 - PATCH ASSESSMENT
# =====================================

@guarded_node("assessment", produces="patch_data")
def patch_assessment_agent(state: PatchState):
    print("[2] Patch Assessment Agent")
    used = charge_tool_call(state, "patch.get_patch_info")
    return {"patch_data": get_patch_info(), "tool_calls": used}

# =====================================
# AGENT 3 - RISK ANALYSIS  (LLM + structured output)
# =====================================

@resilient(timeout=LLM_TIMEOUT)
def _classify_risk(patch_data: dict) -> RiskDecision:
    structured_llm = llm.with_structured_output(RiskDecision)
    return structured_llm.invoke([
        SystemMessage(content="Classify patch risk. HIGH if critical=True."),
        HumanMessage(content=f"Patch data: {patch_data}"),
    ])


@guarded_node("risk", produces="risk_level")
def risk_analysis_agent(state: PatchState):
    print("[3] Risk Analysis Agent  (LLM)")
    try:
        decision = _classify_risk(state["patch_data"])
        return {"risk_level": decision.risk_level, "risk_reason": decision.reason}
    except NodeFailure as exc:
        # deterministic fallback keeps the run going and fails safe to HIGH
        print(f"    [fallback] risk classification unavailable: {exc}")
        critical = bool(state["patch_data"].get("critical"))
        return {
            "risk_level": "HIGH" if critical else "LOW",
            "risk_reason": "rule-based fallback (LLM unavailable)",
            "errors": state.get("errors", []) + [f"risk: LLM fallback used ({exc})"],
        }

# =====================================
# AGENT 4 - RUNBOOK  (RAG)
# =====================================

@guarded_node("runbook", produces="runbook")
def runbook_agent(state: PatchState):
    print("[4] Runbook Agent  (RAG)")
    used = charge_tool_call(state, "runbook.retrieve")
    return {"runbook": retrieve_runbook(state["patch_data"]["os"]), "tool_calls": used}

# =====================================
# AGENT 5 - HUMAN APPROVAL  (HITL, timeout-bounded)
# =====================================

def _ask_human() -> str:
    return input("    Approve patch? (yes/no): ").strip().lower()


@guarded_node("approval", produces="approval")
def approval_agent(state: PatchState):
    print("[5] Human Approval Agent")
    print(f"    Risk: {state['risk_level']} — {state['risk_reason']}")
    print(f"    Runbook:\n{state['runbook']}")
    try:
        approval = _executor.submit(_ask_human).result(timeout=HITL_TIMEOUT)
    except FutureTimeout:
        # fail-safe: no answer in time means no patch is applied
        print(f"    [HITL] no response in {HITL_TIMEOUT}s -> auto-deny")
        return {
            "approval": "timeout",
            "status": "aborted",
            "errors": state.get("errors", []) + ["approval: HITL timed out"],
        }
    return {"approval": approval}

# =====================================
# CONDITIONAL EDGE - approved?
# =====================================

def approval_router(state: PatchState):
    if state.get("status") in ("failed", "aborted"):
        return "fail"
    return "remediation" if state.get("approval") == "yes" else "end"

# =====================================
# AGENT 6 - REMEDIATION
# =====================================

@guarded_node("remediation")
def remediation_agent(state: PatchState):
    print("[6] Remediation Agent")
    attempts = state.get("remediation_attempts", 0) + 1
    if attempts > MAX_REMEDIATION_ATTEMPTS:
        raise BudgetExceeded(f"remediation exceeded {MAX_REMEDIATION_ATTEMPTS} attempts")
    used = charge_tool_call(state, "patch.apply_patches")
    result = apply_patches(state["runbook"], state["idempotency_key"])
    return {
        "remediation": result,
        "remediation_attempts": attempts,
        "tool_calls": used,
        "validation": "",  # cleared so the retry loop re-validates
    }

# =====================================
# AGENT 7 - VALIDATION
# =====================================

@guarded_node("validation")
def validation_agent(state: PatchState):
    print("[7] Validation Agent")
    used = charge_tool_call(state, "health.check_services")
    return {"validation": check_service_health(), "tool_calls": used}

# =====================================
# CONDITIONAL EDGE - validation healthy?
# =====================================

def validation_router(state: PatchState):
    if state.get("status") == "failed":
        return "rollback"
    if state.get("validation") == "Services Healthy":
        return "compliance"
    if state.get("remediation_attempts", 0) < MAX_REMEDIATION_ATTEMPTS:
        return "retry"
    return "rollback"

# =====================================
# ROLLBACK
# =====================================

def rollback_agent(state: PatchState):
    print("[7b] Rollback Agent")
    try:
        result = rollback_patches(state.get("idempotency_key", "unknown"))
    except NodeFailure as exc:
        result = f"ROLLBACK FAILED - page on-call: {exc}"
    return {
        "remediation": result,
        "status": "rolled_back",
        "errors": state.get("errors", []) + ["validation failed after max remediation attempts"],
    }

# =====================================
# AGENT 8 - COMPLIANCE  (LLM)
# =====================================

def compliance_agent(state: PatchState):
    print("[8] Compliance Agent  (LLM)")
    summary = (
        f"Patch: {state.get('patch_data')} | Risk: {state.get('risk_level')} | "
        f"Approval: {state.get('approval')} | Remediation: {state.get('remediation')} | "
        f"Validation: {state.get('validation')} | Status: {state.get('status')} | "
        f"Errors: {state.get('errors')}"
    )
    try:
        report = call_llm([
            SystemMessage(content="You write concise 3-line audit reports for patch runs."),
            HumanMessage(content=summary),
        ])
    except NodeFailure as exc:
        # the audit record must exist even if the LLM is down
        report = f"[RAW AUDIT - LLM unavailable: {exc}]\n{summary}"
    return {
        "compliance_report": report,
        "status": state.get("status") if state.get("status") in ("failed", "rolled_back") else "completed",
    }

# =====================================
# TERMINAL FAILURE HANDLER
# =====================================

def failure_handler(state: PatchState):
    print("[X] Failure handler - escalating to on-call")
    return {
        "status": state.get("status", "failed"),
        "remediation": state.get("remediation") or "NOT EXECUTED - escalated to on-call",
    }

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
builder.add_node("rollback", rollback_agent)
builder.add_node("compliance", compliance_agent)
builder.add_node("failure", failure_handler)

builder.set_entry_point("supervisor")


def continue_or_fail(next_node: str):
    """Short-circuit the linear path to the failure handler once a node has failed."""
    def router(state: PatchState):
        return "fail" if state.get("status") in ("failed", "aborted") else next_node
    return router


builder.add_edge("supervisor", "assessment")
builder.add_conditional_edges("assessment", continue_or_fail("risk"),
                              {"risk": "risk", "fail": "failure"})
builder.add_conditional_edges("risk", continue_or_fail("runbook"),
                              {"runbook": "runbook", "fail": "failure"})
builder.add_conditional_edges("runbook", continue_or_fail("approval"),
                              {"approval": "approval", "fail": "failure"})

builder.add_conditional_edges(
    "approval",
    approval_router,
    {"remediation": "remediation", "end": END, "fail": "failure"},
)

builder.add_conditional_edges("remediation", continue_or_fail("validation"),
                              {"validation": "validation", "fail": "failure"})

# bounded retry loop: validation can send the run back to remediation at most
# MAX_REMEDIATION_ATTEMPTS times, otherwise it rolls back
builder.add_conditional_edges(
    "validation",
    validation_router,
    {"compliance": "compliance", "retry": "remediation", "rollback": "rollback"},
)

builder.add_edge("rollback", "compliance")
builder.add_edge("compliance", END)
builder.add_edge("failure", END)

graph = builder.compile(checkpointer=memory)

# =====================================
# EXECUTION
# =====================================

if __name__ == "__main__":
    config = {
        "configurable": {"thread_id": "PATCH-2026-001"},
        "recursion_limit": RECURSION_LIMIT,   # terminates runaway loops
    }
    try:
        final_state = graph.invoke({}, config=config)
    except Exception as exc:
        print(f"\n=== RUN ABORTED: {type(exc).__name__}: {exc} ===")
        final_state = graph.get_state(config).values  # fall back to last checkpoint

    print("\n=== FINAL STATE ===")
    for k, v in final_state.items():
        print(f"{k}: {v}")
