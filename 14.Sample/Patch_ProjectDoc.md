# Project 2 — Patch Management Automation (Patch.py)

## 1. What is the Use Case?

Enterprises need to keep servers patched for security and compliance. Today, the
patching process is largely manual:
- Someone checks how many patches are missing and whether any are critical.
- A senior engineer assesses risk.
- An operator opens the standard runbook / SOP for patching.
- A change manager approves the patch window.
- An operator installs patches and restarts services.
- Someone validates that services are healthy.
- A compliance report is prepared for audit.

**Use case:** Automate this end-to-end patch management workflow — assessment,
risk analysis, runbook retrieval, approval, remediation, validation, and
compliance reporting — with a human approval gate before any change is applied.

---

## 2. What Solution Are We Implementing?

We are implementing an **Agentic AI workflow using LangGraph's Supervisor
pattern**. A **Supervisor Agent** oversees the flow, and specialized agents handle
each stage of patching:

- **Patch Assessment Agent** pulls missing/critical patch info via an **MCP tool**.
- **Risk Analysis Agent** classifies risk (HIGH / LOW).
- **RAG / Runbook Agent** retrieves the operational runbook (SOP).
- **Human Approval Agent** takes a go/no-go decision.
- **Remediation Agent** installs patches.
- **Validation Agent** confirms service health.
- **Compliance Agent** produces the audit report.
- **MemorySaver** checkpoints state so the workflow is resumable.

**Why Agentic AI?** Patch management is a multi-step operational process with
tool calls, retrieved knowledge (runbooks), conditional decisions, and mandatory
human approval before any change action. That is exactly what agentic workflows
are for.

---

## 3. Concept / Technology Mapping Table

| Concept | Implementation in This Project | Purpose |
|---|---|---|
| Problem | Manual patching + manual compliance reporting | Slow, risky, inconsistent |
| Agentic AI | Supervisor + specialized agents in LangGraph | Automate multi-stage patching |
| LangGraph | `StateGraph(PatchState)` with 8 nodes + conditional edge | Orchestrate the workflow |
| Architecture | Supervisor → Assessment → Risk → Runbook → Approval → Remediation → Validation → Compliance | End-to-end patching |
| Agents | `supervisor_agent`, `patch_assessment_agent`, `risk_analysis_agent`, `runbook_agent`, `approval_agent`, `remediation_agent`, `validation_agent`, `compliance_agent` | Divide responsibilities |
| State Management | `PatchState` `TypedDict` | Carry patch data through the graph |
| Routing / Conditional Routing | `approval_router` after the approval node | Gate remediation on human decision |
| Tools / Tool Calling | `get_patch_info()`, `retrieve_runbook()` | External / operational data |
| MCP | `get_patch_info` (patch data) and `retrieve_runbook` (runbook) treated as MCP tools | Standardized tool access |
| RAG | `runbook_agent` retrieves the runbook / SOP text | Ground remediation in approved procedures |
| Human-in-the-Loop | `approval_agent()` with `input(...)` | Explicit human sign-off |
| LLM | Represented by agent nodes (analysis / risk / runbook / remediation reasoning) | Reasoning steps |
| Structured Outputs | `TypedDict` state with typed fields | Predictable data contract |
| Validation / Safeguards | `validation_agent` + `compliance_agent` + Approval gate | Post-change checks + audit trail |
| Persistence / Memory | `MemorySaver()` checkpointer | Resumable, durable workflow |
| Supervisor Pattern | `supervisor_agent` as workflow overseer | Governance of the multi-agent flow |
| Error Handling | `@guarded_node` on every agent | Failures become state, not crashes |
| Retry Logic | `@resilient(timeout, retries)` on every tool / LLM call | Bounded exponential backoff + jitter |
| Timeouts | `TOOL_TIMEOUT` / `LLM_TIMEOUT` / `HITL_TIMEOUT` | No call or human can hang the graph |
| Idempotency | `produces=` on `@guarded_node` + `idempotency_key` | A node never re-runs after it has produced its output |
| Budgets / Limits | `MAX_TOOL_CALLS`, `MAX_NODE_ATTEMPTS`, `MAX_REMEDIATION_ATTEMPTS`, `recursion_limit` | Hard termination guarantees |
| Rollback | `rollback_agent` + `validation_router` | Undo a bad patch after retries are exhausted |

---

## 4. Problem

Without this system:

- Patch discovery is manual — someone runs a tool or a script to see what's missing.
- Risk classification is judgment-based and inconsistent.
- Runbook lookup is a separate manual step, often across wikis or SOP docs.
- Approval is chased over email/chat and often not linked to the actual change.
- Remediation is performed by hand; mistakes are common.
- Post-change validation is inconsistent.
- Compliance evidence is compiled after the fact and may be incomplete.

Difficulties:

- **Slow patch cycles** → unpatched CVEs stay open.
- **No consistent risk assessment**.
- **No traceable approval** tied to the change.
- **No automatic validation or audit trail**.
- **No resumability** if the operator is interrupted mid-flow.

---

## 5. Why Agentic AI?

A single LLM call cannot handle patching end-to-end. The workflow needs:

1. **Multiple specialized steps** — assessment, risk, runbook, approval,
   remediation, validation, compliance.
2. **Tool calling** — `get_patch_info()` and `retrieve_runbook()`.
3. **Retrieved knowledge (RAG-style)** — the runbook must ground the remediation.
4. **Conditional decision** — approval gate (`approval_router`) decides whether
   remediation runs at all.
5. **Human collaboration** — `approval_agent` blocks on a real user answer.
6. **Shared state across steps** — every agent contributes to `PatchState`.

An agentic pattern (Supervisor + workers + tools + state + routing) matches this
naturally.

---

## 6. Why LangGraph?

LangGraph gives an explicit, inspectable graph with typed state — which fits the
Supervisor pattern used here.

- **Supervisor pattern:** `supervisor_agent` is the entry point that oversees the
  workflow.
- **State management:** `StateGraph(PatchState)` shares a single `TypedDict`
  across all agents.
- **Nodes as agents:** every agent
  (`supervisor`, `assessment`, `risk`, `runbook`, `approval`, `remediation`,
  `validation`, `compliance`) is a graph node.
- **Conditional edges:** `add_conditional_edges("approval", approval_router, ...)`
  enforces the human gate.
- **Human-in-the-Loop:** the approval node blocks on `input()` — its answer
  drives the next edge.
- **Post-change validation & compliance** are modeled as their own downstream nodes.
- **Resumability / persistence:** `builder.compile(checkpointer=memory)` with
  `MemorySaver()`.

---

## 7. Architecture

```
                +------------------+
                |       User       |
                +------------------+
                          |
                          v
                +--------------------+
                | Supervisor Agent   |
                +--------------------+
                          |
                          v
                +--------------------------+
                | Patch Assessment Agent   |
                | -> get_patch_info() (MCP)|
                +--------------------------+
                          |
                          v
                +----------------------+
                | Risk Analysis Agent  |
                | (HIGH / LOW)         |
                +----------------------+
                          |
                          v
                +----------------------+
                |  RAG / Runbook Agent |
                | -> retrieve_runbook()|
                +----------------------+
                          |
                          v
                +----------------------+
                |   Approval Agent     |
                |   (Human in Loop)    |
                +----------------------+
                          |
                          v
                +----------------------+
                |  approval == yes ?   |
                +----------------------+
                    |            |
                 YES|            |NO
                    v            v
        +--------------------+  +-------+
        | Remediation Agent  |  |  END  |
        | (Install patches)  |  +-------+
        +--------------------+
                    |
                    v
        +--------------------+
        |  Validation Agent  |
        | (Service Health)   |
        +--------------------+
                    |
                    v
        +--------------------------+
        |   Services Healthy ?     |
        +--------------------------+
           |          |          |
        YES|   retry  |          | attempts exhausted
           |  (<= 2)  |          |
           |          v          v
           |   [ Remediation ]  +------------------+
           |                    | Rollback Agent   |
           |                    +------------------+
           |                             |
           v                             v
        +--------------------------+ <---+
        | Compliance Report Agent  |
        +--------------------------+
                    |
                    v
                +-------+
                |  END  |
                +-------+

  Any node failure / budget breach -> [ Failure Handler ] -> END

     [ MemorySaver checkpointer wraps the whole graph ]
```

Components: Supervisor + 7 worker agents, LangGraph `StateGraph`, `PatchState`
`TypedDict`, MCP tools (`get_patch_info`, `retrieve_runbook`), HITL approval,
`MemorySaver`.

---

## 8. Workflow

Step-by-step:

1. **Invoke** — `graph.invoke({})`.
2. **Supervisor node** — logs "Supervisor Monitoring Workflow" and passes state
   through (governance role).
3. **Patch Assessment node** — calls `get_patch_info()` and stores
   `{"missing_patches": 15, "critical": True}` under `patch_data`.
4. **Risk Analysis node** — inspects `patch_data["critical"]` and sets
   `risk_level = "HIGH"` if critical else `"LOW"`.
5. **Runbook (RAG) node** — calls `retrieve_runbook()` and stores the runbook
   text under `runbook`.
6. **Approval node (HITL)** — prompts *"Approve patch? (yes/no)"* and stores the
   answer under `approval`.
7. **Conditional edge `approval_router`:**
   - `approval == "yes"` → `remediation`.
   - Otherwise → `END`.
8. **Remediation node** — writes `"Patches installed successfully"` to
   `remediation`.
9. **Validation node** — writes `"Services Healthy"` to `validation`.
10. **Compliance node** — logs *"Compliance report generated"*.
11. **END** — final state is checkpointed via `MemorySaver`.

Decision points:

- **Approval gate** (`approval == "yes"`) is the single conditional branch.
- Everything after remediation (validation + compliance) is a fixed chain.

---

## 9. Agents

| Agent | Responsibility | Input | Output | Tools Used |
|---|---|---|---|---|
| `supervisor_agent` | Oversees / kicks off the workflow (Supervisor pattern) | `PatchState` | Unchanged state | — |
| `patch_assessment_agent` | Discover missing / critical patches | `state` | `patch_data` dict | `get_patch_info()` (MCP) |
| `risk_analysis_agent` | Classify risk level | `state["patch_data"]["critical"]` | `risk_level` = "HIGH"/"LOW" | — |
| `runbook_agent` (RAG) | Retrieve operational runbook | `state` | `runbook` text | `retrieve_runbook()` (MCP) |
| `approval_agent` | Get human go/no-go | `state` | `approval` = "yes"/"no" | Console `input()` (HITL) |
| `remediation_agent` | Apply patches (bounded attempts + idempotency key) | `state` | `remediation`, `remediation_attempts` | `apply_patches()` (MCP) |
| `validation_agent` | Confirm services are healthy after patching | `state` | `validation` | `check_service_health()` (MCP) |
| `rollback_agent` | Undo the patch when validation keeps failing | `state` | `remediation`, `status="rolled_back"` | `rollback_patches()` (MCP) |
| `compliance_agent` | Emit compliance/audit report (raw fallback if LLM down) | `state` | `compliance_report`, final `status` | LLM |
| `failure_handler` | Terminal node for failed/aborted runs; escalates to on-call | `state` | `status`, `remediation` note | — |

---

## 10. State Management

The workflow uses a single typed state object:

```python
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
    status: str                   # running | completed | failed | aborted | rolled_back
    failed_node: str
    errors: List[str]
    tool_calls: int
    node_attempts: Dict[str, int]
    remediation_attempts: int
    idempotency_key: str
```

How information flows:

- `patch_assessment_agent` adds `patch_data`.
- `risk_analysis_agent` adds `risk_level`.
- `runbook_agent` adds `runbook`.
- `approval_agent` adds `approval`.
- `remediation_agent` adds `remediation`.
- `validation_agent` adds `validation`.
- `compliance_agent` reads state and produces the report.

Each node returns a partial dict; LangGraph merges it into the shared `PatchState`
so every downstream node sees earlier findings (patch data, risk level, runbook,
approval, remediation, validation).

**Persistence:** `MemorySaver()` is attached via
`builder.compile(checkpointer=memory)`, giving durable checkpointing and
resumability.

---

## 11. Routing Logic

Static edges (fixed sequence):

- `set_entry_point("supervisor")`
- `supervisor → assessment`
- `assessment → risk`
- `risk → runbook`
- `runbook → approval`
- `remediation → validation`
- `validation → compliance`
- `compliance → END`

Conditional edges:

1. **`approval_router`** (after `approval`):
   - `state["approval"] == "yes"` → `"remediation"`.
   - Anything else → `END`.

Where the workflow can branch, stop, or continue:

- **Approval branch:** if the human says "no" (or times out), the workflow
  *stops* before any change; if "yes", it continues to remediation.
- **Validation branch (`validation_router`):**
  - `validation == "Services Healthy"` → `compliance`.
  - unhealthy **and** `remediation_attempts < MAX_REMEDIATION_ATTEMPTS` →
    `remediation` (bounded retry loop).
  - unhealthy **and** attempts exhausted → `rollback` → `compliance`.
- **Failure short-circuit (`continue_or_fail`):** after every linear step, if
  `status` is `failed`/`aborted` the graph jumps to the terminal `failure`
  node and ends.

---

## 11b. Error Handling, Retries, Idempotency & Termination

### Config knobs (top of `Patch.py`)

| Constant | Value | Purpose |
|---|---|---|
| `MAX_RETRIES` | 3 | Attempts per tool / LLM call |
| `RETRY_BASE_DELAY` / `RETRY_MAX_DELAY` | 1.0s / 8.0s | Exponential backoff with jitter |
| `TOOL_TIMEOUT` | 15s | Hard timeout per MCP tool call |
| `LLM_TIMEOUT` | 45s | Hard timeout per LLM call |
| `HITL_TIMEOUT` | 300s | Max wait for approval, then auto-deny |
| `MAX_TOOL_CALLS` | 20 | Tool-call budget for the whole run |
| `MAX_NODE_ATTEMPTS` | 2 | **How often any single node may execute in a run** |
| `MAX_REMEDIATION_ATTEMPTS` | 2 | Patch install attempts before rollback |
| `RECURSION_LIMIT` | 30 | LangGraph super-step limit (runaway-loop guard) |

### 1. Retry logic — `@resilient(timeout, retries)`
Every MCP tool and LLM call is wrapped. It submits the call to a thread pool
and enforces a **hard timeout**, then retries with **exponential backoff +
jitter** (1s → 2s → 4s, capped at 8s). When attempts are exhausted it raises
`NodeFailure`. The LLM client is configured with `max_retries=0` so the
provider SDK does not silently multiply the retry count (3 × 3 = 9 calls).
The change actions (`apply_patches`, `rollback_patches`) get `retries=1` —
change operations are **not** blindly retried; the explicit remediation loop
owns that decision.

### 2. Error handling — `@guarded_node(name, produces=...)`
Every agent is wrapped. It catches `NodeFailure`, `BudgetExceeded`,
`KeyError`, `ValueError` and writes `status="failed"`, `failed_node`, and an
`errors[]` entry into state instead of raising. The graph then routes to the
terminal `failure` node. Graceful degradation is used where an audit record
matters more than the LLM:
- **Risk Agent** — if the LLM fails, falls back to the deterministic rule
  (`critical == True` → HIGH) and logs the fallback in `errors[]`.
- **Compliance Agent** — if the LLM fails, emits a raw (non-prose) audit
  record so compliance evidence always exists.

### 3. Stopping a node from running multiple times
This is the **idempotency guard**, and there are four layers:

1. **`produces="<state key>"`** — `@guarded_node("runbook", produces="runbook")`
   skips the node entirely if that key is already populated. On a resume,
   replay, or re-invoke of the same `thread_id`, assessment / risk / runbook /
   approval will **not** call their tools again.
2. **`node_attempts` counter in state** — every execution increments
   `state["node_attempts"][node]`; past `MAX_NODE_ATTEMPTS` it raises
   `BudgetExceeded`. This caps even the nodes that are legitimately in a loop
   (remediation / validation).
3. **`idempotency_key`** — the supervisor derives a stable key per run
   (sha256 of the run identity). It is passed to `apply_patches()` and
   `rollback_patches()` so a *downstream* system can de-duplicate a repeated
   change request even if the agent retries.
4. **Status gate** — once `status` is `failed`/`aborted`, every guarded node
   returns `{}` immediately, so no further side effects happen.

### 4. Max tool call limit
`charge_tool_call(state, tool_name)` increments `state["tool_calls"]` before
*every* MCP invocation and raises `BudgetExceeded` past `MAX_TOOL_CALLS = 20`.
This is the cost/loop ceiling for the run and applies across all MCP servers.

### 5. Termination conditions
The run always ends in one of these states:

| Condition | Resulting `status` | Side effect |
|---|---|---|
| All nodes complete | `completed` | Patched + validated + report |
| Human denies approval | (unset) → `END` | No change |
| HITL timeout (300s) | `aborted` | No change (fail-safe deny) |
| Any node exhausts retries | `failed` | `failure` node, escalate to on-call |
| Node re-run cap hit | `failed` (`BudgetExceeded`) | `failure` node |
| Tool budget exhausted | `failed` (`BudgetExceeded`) | `failure` node |
| Validation unhealthy after max attempts | `rolled_back` | Rollback executed, report written |
| Runaway loop | `GraphRecursionError` at `recursion_limit = 30` | Falls back to last checkpoint |

Every ambiguous outcome **fails safe** — nothing is patched.

### 6. Checkpoint fallback
`graph.invoke` is wrapped in `try/except`; on an unexpected abort the last
good checkpoint is recovered with `graph.get_state(config).values` so the
audit trail is never lost.

---

## 12. Tool Integrations

| Tool / Service | Used By | Purpose | Input | Output |
|---|---|---|---|---|
| `get_patch_info()` (MCP) | `patch_assessment_agent` | Return missing/critical patch info | — | `{"missing_patches": 15, "critical": True, "os": "RHEL8"}` |
| `retrieve_runbook()` (MCP / RAG) | `runbook_agent` | Return runbook / SOP for patching | `patch_type` | Runbook text |
| `apply_patches()` (MCP) | `remediation_agent` | Execute the patch install | runbook + `idempotency_key` | Install result |
| `check_service_health()` (MCP) | `validation_agent` | Post-change health probe | — | `"Services Healthy"` / unhealthy |
| `rollback_patches()` (MCP) | `rollback_agent` | Undo a failed patch | `idempotency_key` | Rollback result |
| Console `input()` | `approval_agent` | Capture human approval (300s timeout) | Prompt string | `"yes"` / `"no"` / `"timeout"` |
| `MemorySaver` (LangGraph) | Graph runtime | Checkpoint workflow state | State snapshot | Persisted checkpoint |

All tool stubs are wrapped with `@resilient(...)` and counted via
`charge_tool_call()`.

### MCP servers used in this workflow

| MCP Server | Tools exposed | Backing system (prod) | Used by | Guardrails |
|---|---|---|---|---|
| **Patch MCP** | `get_patch_info`, `apply_patches`, `rollback_patches` | SCCM / WSUS / Red Hat Satellite / Ansible Tower | Assessment, Remediation, Rollback | 15s timeout; read tools 3 retries, change tools 1 retry + idempotency key |
| **Runbook / RAG MCP** | `retrieve_runbook` (vector search over Runbooks / SOP / KB / SharePoint) | Vector store + SharePoint/Confluence | Runbook Agent | 15s timeout, 3 retries, **fail closed** on empty runbook |
| **Monitoring / Health MCP** | `check_service_health` | Prometheus / Nagios / Datadog | Validation Agent | 15s timeout, 3 retries |
| **Approval MCP** (prod) | `request_approval` via ServiceNow change / Slack / Teams | ServiceNow CHG + chat ops | Approval Agent | `HITL_TIMEOUT` 300s → auto-deny |
| **Compliance MCP** (prod) | `submit_audit_report` | Immutable audit store / GRC tool | Compliance Agent | retries + local buffer fallback |

In the POC these are **plain Python stubs** labelled `[MCP]` — no MCP server is
actually running. In production they would be loaded with
`langchain-mcp-adapters`; the agent code does not change, only the tool
implementation moves behind the MCP protocol.

The `MAX_TOOL_CALLS = 20` budget applies across every MCP server in a run.

---

## 13. Human-in-the-Loop / Safety Controls

Human approval is enforced by `approval_agent`:

- Placed **after** assessment, risk analysis, and runbook retrieval, so the human
  approves *with full context in state* (missing patches, criticality, risk
  level, and the runbook to be followed).
- Blocks on `input("Approve patch? (yes/no): ")`.
- If `"yes"` → `remediation_agent` runs.
- If anything else → routed to `END`, and no change action is executed.

Safeguards separating investigation from operational remediation:

- **Assessment**, **Risk Analysis**, and **Runbook** agents are read-only /
  informational — they don't change anything.
- **Remediation** is gated behind the approval router.
- **Validation** confirms system health *after* the change.
- **Compliance** provides the audit trail.

---

## 14. End-to-End Solution Design

```
Input: {}
      |
      v
LangGraph Workflow (StateGraph + MemorySaver, Supervisor pattern)
      |
      v
Agents: Supervisor -> Assessment -> Risk -> Runbook -> Approval
                    -> Remediation -> Validation -> Compliance
      |
      v
State: PatchState (patch_data, risk_level, runbook, approval, remediation, validation)
      |
      v
Routing / Decisions:
   - approval_router (approval == "yes")
      |
      v
Tools / RAG / APIs:
   - get_patch_info()      (MCP)
   - retrieve_runbook()    (MCP / RAG runbook)
      |
      v
Human Approval: approval_agent (blocking input)
      |
      v
Remediation / Final Action: "Patches installed successfully"
      |
      v
Validation / Reporting: "Services Healthy" + Compliance report
      |
      v
Persistence: MemorySaver checkpoints final state
```

---

## 15. Business Value

Based on what is actually implemented:

- **Reduced manual effort** — no manual patch scan, risk call, runbook lookup, or
  audit report assembly.
- **Faster investigation** — assessment, risk, and runbook retrieval run
  back-to-back with shared state.
- **Consistency** — every patch cycle runs the same 8 nodes in the same order.
- **Operational efficiency** — human effort is focused on the approval decision.
- **Safety** — change is gated behind an explicit approval and is followed by a
  validation step.
- **Auditability** — `PatchState` captures patch data, risk, runbook used,
  approval, remediation result, and validation result; the compliance agent
  emits the report; `MemorySaver` checkpoints the state.
- **Standardization** — runbook is retrieved and stored in state, so the same
  SOP grounds every remediation.

---

## 16. Interview Explanation

### 30-second explanation
> I built a patch management workflow in LangGraph using the Supervisor pattern.
> A supervisor agent oversees specialized agents that assess patches, analyze
> risk, retrieve the runbook via a RAG/MCP tool, get human approval, install
> patches, validate service health, and generate a compliance report. State is a
> `TypedDict` and is persisted with `MemorySaver`.

### 1-minute explanation
> The workflow starts with a Supervisor Agent. The Patch Assessment Agent calls
> an MCP tool `get_patch_info()` to get missing/critical patch info. The Risk
> Analysis Agent classifies risk as HIGH or LOW based on criticality. The Runbook
> Agent uses an MCP tool `retrieve_runbook()` — this is the RAG step, grounding
> the workflow in the approved SOP. Then the Human Approval Agent blocks on a
> `yes/no` input. A conditional edge `approval_router` sends the workflow to the
> Remediation Agent only if the human said `"yes"`; otherwise it ends. After
> remediation, the Validation Agent confirms services are healthy and the
> Compliance Agent generates the audit report. The graph is compiled with a
> `MemorySaver` checkpointer for durable, resumable execution.

### 2-minute detailed explanation
> The problem is that enterprise patching is manual and inconsistent: someone
> checks patches, someone else assesses risk, an operator looks up the runbook,
> approval is chased over chat, patches are installed by hand, validation is
> ad-hoc, and audit evidence is compiled later. I built an Agentic AI workflow
> in LangGraph using the Supervisor pattern to automate this.
>
> The state is a `PatchState` `TypedDict` with `patch_data`, `risk_level`,
> `runbook`, `approval`, `remediation`, and `validation`. I built a `StateGraph`
> and added eight nodes: `supervisor`, `assessment`, `risk`, `runbook`,
> `approval`, `remediation`, `validation`, and `compliance`.
>
> The Supervisor Agent is the entry point — it oversees the workflow (that's the
> Supervisor pattern). The Patch Assessment Agent calls an MCP tool
> `get_patch_info()` and writes the result into `patch_data`. The Risk Analysis
> Agent reads `patch_data["critical"]` and sets `risk_level` to `"HIGH"` or
> `"LOW"`. The Runbook Agent is the RAG step — it calls
> `retrieve_runbook()` (treated as an MCP tool) and stores the SOP text in
> `runbook`, so any downstream remediation is grounded in approved procedure.
>
> The Approval Agent is Human-in-the-Loop — it blocks on `input()` and stores
> `yes/no` in state. A conditional edge `approval_router` routes to the
> Remediation Agent only if the answer is `"yes"`, otherwise it goes straight to
> `END`. This is the single safety gate: no change happens without an explicit
> human `yes`. If approved, the Remediation Agent writes `"Patches installed
> successfully"`, the Validation Agent writes `"Services Healthy"`, and the
> Compliance Agent generates the audit report.
>
> The graph is compiled with `MemorySaver` as the checkpointer, giving durable
> state and resumability. So the design covers assessment, risk, RAG-grounded
> runbook retrieval, HITL approval, remediation, validation, and compliance in a
> single auditable, resumable workflow.

### Important follow-up questions an interviewer may ask

**Q1. What is the Supervisor pattern, and how does `supervisor_agent` differ from a plain orchestrator?**
The Supervisor pattern is a LangGraph multi-agent style where one agent sits at the top of the graph and decides which specialist agent runs next (delegation). A plain orchestrator only runs a fixed sequence of steps. In this POC the `supervisor_agent` is the entry point and oversees the flow; the specialist agents (assessment, risk, runbook, approval, remediation, validation, compliance) handle their narrow tasks. In production the supervisor would use an LLM to *route dynamically* (e.g., skip runbook lookup if patch is trivial); in the POC the routing is static edges, which is a simplified supervisor.

**Q2. Where exactly is RAG used in this project, and why does it matter?**
RAG lives in the **Runbook Agent** — `retrieve_runbook()` fetches the approved SOP for the patch type and writes it into `state["runbook"]`. It matters because remediation must be grounded in an *approved procedure*, not in freeform LLM output. Without RAG, the remediation agent could hallucinate unsafe commands. RAG guarantees the patch install steps come from the SOP library (runbooks, KB, SharePoint). In production this becomes a vector store (embeddings + hybrid BM25/dense retrieval + reranking) over the runbook corpus.

**Q3. Why is the approval node placed *after* assessment, risk, and runbook — and not earlier?**
Because a human can only make an informed go/no-go decision *after* seeing (a) what patches are missing, (b) the risk level, and (c) the exact runbook that will be executed. Asking for approval earlier would be a blind sign-off. Placing approval after these three enrichments means the human sees a complete change record and can approve with context. It also makes the audit trail clean — the state captured at approval time contains everything the human saw.

**Q4. What does `MemorySaver` give you here? Would you use it in production?**
`MemorySaver` is LangGraph's in-memory checkpointer. Every node transition is persisted as a checkpoint tied to a `thread_id`. Benefits: (1) **Resumability** — if the approval step is left hanging overnight, the workflow resumes from the last checkpoint. (2) **HITL pause/resume** — the graph can suspend at the approval node and resume when the human responds. (3) **Audit** — the full state history is inspectable. In production I'd swap it for a durable backend — `SqliteSaver` for single-node or `PostgresSaver` for multi-instance/HA — because `MemorySaver` is process-local and lost on restart.

**Q5. What happens if the human rejects approval? What state has been captured?**
The `approval_router` returns `"end"` and the graph goes to `END` without touching `remediation`, `validation`, or `compliance`. The state at that point already contains `patch_data`, `risk_level`, `runbook`, and `approval="no"` — so the audit trail proves that assessment ran, risk was analyzed, the correct runbook was retrieved, and a human explicitly declined. That's a valid audit record for compliance ("change proposed and rejected"). No side effect touched the servers.

**Q6. How is unsafe remediation prevented?**
Four layers: (1) **Approval gate** — no `remediation_agent` execution without `approval == "yes"`. (2) **RAG-grounded steps** — remediation follows the retrieved runbook, not free-form LLM output. (3) **Validation agent** — runs immediately after remediation to confirm services are healthy; a failure surfaces in state. (4) **Compliance agent** — writes an audit record for every run. In production add a fifth: a canary/staged rollout or a rollback branch on validation failure.

**Q7. How would you replace the mock `get_patch_info()` and `retrieve_runbook()` with real MCP servers?**
Stand up two MCP servers exposing tools over stdio/HTTP: (a) a **Patch MCP server** wrapping SCCM / WSUS / Ansible Tower / Satellite APIs that returns missing/critical patches for a host; (b) a **Runbook MCP server** wrapping the vector store over SharePoint/Confluence/KB with a `retrieve_runbook(patch_type)` tool. On the LangGraph side, use `langchain-mcp-adapters` to load the MCP tools and call them from the assessment and runbook agents. The agents' code doesn't change — only the tool implementations move behind the MCP protocol.

**Q8. How would you plug an actual LLM into the risk / runbook / remediation reasoning?**
- **Risk Agent** — LLM (Gemini 2.5 / GPT-4o) reads `patch_data` and returns a structured `risk_level` via `with_structured_output(RiskDecision)` (Pydantic model with fields `risk_level`, `reason`, `cve_severity`).
- **Runbook Agent** — LLM summarizes the retrieved runbook into an executable step list (RAG post-processing).
- **Remediation Agent** — LLM plans the command sequence from the runbook steps and calls a `run_command` tool (with allow-listed commands only).
Each LLM call is wrapped in `try/except` with a fallback to a deterministic rule, so the graph never wedges on an LLM error.

**Q9. How would you handle a remediation failure — where would retries or a rollback branch go?**
**Implemented.** A conditional edge `validation_router` sits after
`validation_agent`:
- `validation == "Services Healthy"` → `compliance`.
- unhealthy and `remediation_attempts < MAX_REMEDIATION_ATTEMPTS` → back to
  `remediation` (the remediation node clears `validation` so the loop
  re-validates).
- attempts exhausted → `rollback_agent` (calls `rollback_patches()` with the
  run's `idempotency_key`) → `compliance`, with `status="rolled_back"`.
The loop is bounded three ways: `remediation_attempts`, `node_attempts`
(`MAX_NODE_ATTEMPTS`), and LangGraph's `recursion_limit = 30`.

**Q9b. How do you make sure an agent/node does not run multiple times?**
Four layers: (1) `@guarded_node(name, produces="key")` skips the node if its
output key is already in state — critical on resume/replay of the same
`thread_id`; (2) a `node_attempts` counter in state caps each node at
`MAX_NODE_ATTEMPTS = 2`; (3) an `idempotency_key` is passed to the change
tools so the downstream system can de-duplicate a repeated patch request;
(4) once `status` is `failed`/`aborted`, every guarded node returns `{}`
immediately so no further side effects occur.

**Q9c. What is your retry policy, and why not just retry everything?**
Read-only tools (`get_patch_info`, `retrieve_runbook`, `check_service_health`)
and LLM calls get 3 attempts with jittered exponential backoff and a hard
timeout. Change tools (`apply_patches`, `rollback_patches`) get only 1 retry
because blindly retrying a change can double-apply it — retry there is an
explicit graph-level decision (`validation_router`) with an idempotency key,
not a silent loop. The LLM client is set to `max_retries=0` so SDK retries
don't multiply the configured count.

**Q9d. What are your termination conditions and tool-call limits?**
`MAX_TOOL_CALLS = 20` (enforced by `charge_tool_call` → `BudgetExceeded`),
`MAX_NODE_ATTEMPTS = 2` per node, `MAX_REMEDIATION_ATTEMPTS = 2`,
`HITL_TIMEOUT = 300s` (auto-deny), per-call `TOOL_TIMEOUT`/`LLM_TIMEOUT`, and
`recursion_limit = 30` passed in the invoke config. Terminal states are
`completed`, `aborted`, `failed`, and `rolled_back` — and every ambiguous
outcome fails safe with no patch applied.

**Q10. What structured outputs are you using?**
The shared state is a `TypedDict` (`PatchState`) with fixed keys: `patch_data: dict`, `risk_level: str`, `runbook: str`, `approval: str`, `remediation: str`, `validation: str`. Every agent returns a partial dict that LangGraph merges into state — that partial is effectively a structured output. In production I'd tighten `patch_data` and `risk_level` to Pydantic models (`PatchInfo`, `RiskDecision`) and use `llm.with_structured_output(Model)` so the LLM is forced to emit valid JSON matching the schema.

**Q11. How would you extend the approval flow to route based on `risk_level` (e.g., auto-approve LOW, require HITL only for HIGH)?**
Add a conditional edge before the approval node — call it `risk_router` — with the rule: `risk_level == "HIGH"` → `approval_agent` (HITL), else → `remediation_agent` (auto-approve). This preserves the safety gate for real risk while removing HITL friction on trivial patches. Two extra guardrails: (1) log the auto-approval in state as `approval="auto-low-risk"` for audit; (2) still run validation and compliance on every path.

**Q12. How is this different from the Incident Management project (Langraph.py) — what's added here?**
| Aspect | Langraph.py (Incident Mgmt) | Patch.py (Patch Mgmt) |
|---|---|---|
| Pattern | Linear pipeline with router | **Supervisor pattern** |
| Agents | 5 (Triage, Cmd/Log, Diagnostic, RCA, Remediation) | **8** (adds Supervisor, Validation, Compliance) |
| Trigger | Reactive — ServiceNow incident | Proactive — scheduled patch cycle |
| RAG scope | Runbooks/SOPs/KB for RCA | **Runbook-only** for change execution |
| Post-action | Ends after remediation | **Validation + Compliance report** |
| Audit criticality | Medium (ops event) | **High** (regulated change) |

Patch.py adds the *supervisor* layer, an explicit *validation* step after the change, and a mandatory *compliance* report — because patching is a regulated change activity, whereas incident handling is a reactive investigation.

---

### Additional interview questions you should be ready for

**Q13. Why LangGraph over LangChain agents or CrewAI?**
LangGraph gives you an **explicit typed state graph** with deterministic edges, conditional routing, checkpointing, and native HITL support — everything a regulated change workflow needs. LangChain agents are a single ReAct loop with no graph, no state, no HITL primitive. CrewAI is role-based collaboration but weaker on typed state and checkpointing. For an *auditable* patch workflow, LangGraph wins on state + checkpointer + conditional edges.

**Q14. What is `add_conditional_edges` and why is it central to this design?**
`add_conditional_edges(source, router_fn, mapping)` runs `router_fn(state)` after `source` executes and uses its return value to look up the next node in `mapping`. In this project it powers the `approval_router` — the single decision point that gates real change. Without conditional edges the graph would be a straight line and could not enforce the HITL gate.

**Q15. How does the state get updated — do agents mutate it directly?**
No. Each agent returns a **partial dict** (e.g., `return {"risk_level": "HIGH"}`) and LangGraph merges it into `PatchState` automatically. This immutable-update model makes every transition reproducible and inspectable via the checkpointer.

**Q16. How would you scale this to thousands of servers per night?**
- Run one LangGraph thread per host (`thread_id = host_id`) — the checkpointer isolates state.
- Fan out via a queue (Celery/SQS) and let a worker pool consume host-level jobs.
- Move the checkpointer to `PostgresSaver`.
- Batch the approval step — the approval agent groups by risk cluster and asks the human once per cluster, not per host.
- Add rate limiting on the MCP tool calls to protect SCCM/WSUS.

**Q17. What are the failure modes of this workflow?**
(1) MCP tool timeout on `get_patch_info` — `@resilient` retries 3× with backoff,
then `@guarded_node` marks the run failed and routes to the `failure` node.
(2) Empty/irrelevant runbook — `retrieve_runbook` raises on empty text, so the
workflow **fails closed** and never patches unguided. (3) Human never responds
— `HITL_TIMEOUT = 300s` auto-denies (`status="aborted"`); in production this
becomes a longer timer plus an escalation node. (4) Remediation partial success
— validation catches it, the bounded retry loop re-runs remediation, and
rollback fires when attempts are exhausted. (5) LLM down — the risk agent falls
back to a deterministic rule and the compliance agent emits a raw audit record.
(6) Runaway loop / cost blowup — `MAX_TOOL_CALLS`, `MAX_NODE_ATTEMPTS` and
`recursion_limit` terminate the run.

**Q17b. Additional questions to be ready for**
- Why retry inside a decorator instead of LangGraph's node-level `RetryPolicy`
  (`add_node(..., retry=RetryPolicy(max_attempts=3))`)? — because the decorator
  also gives per-call timeouts and feeds the tool-call budget.
- Which errors do you retry vs fail fast on? (transient I/O & timeouts vs
  schema/validation errors)
- Why jitter in the backoff? (prevents synchronized retry storms across
  thousands of hosts)
- Why is the HITL timeout an auto-**deny** and not an auto-approve?
- How would you add a circuit breaker for a repeatedly failing MCP server?
- What is persisted in the checkpoint when a node times out mid-call?
- How do you alert/page on runs ending in `failed` or `rolled_back`?
- Can an operator raise the tool budget and resume the same `thread_id`?

**Q18. How do you test this workflow?**
- **Unit tests** per agent — mock the tool calls and assert the partial state returned.
- **Graph tests** — invoke the compiled graph with a mocked `input()` for approval and assert final state contains all expected keys.
- **Contract tests** on MCP tools — validate schema of `get_patch_info` / `retrieve_runbook` responses.
- **Golden path + rejection path** — two integration tests: `approval="yes"` reaches compliance; `approval="no"` ends after approval.
- **Regression** on structured outputs when the LLM is wired in.

**Q19. What are the security considerations?**
- **Secrets** — MCP tool credentials (SCCM, ServiceNow, LLM keys) live in a secret manager (Vault/Secrets Manager), never in code.
- **Least privilege** — the remediation MCP tool holds a scoped service account per host cluster.
- **Command allow-list** — the remediation agent can only execute commands present in the retrieved runbook.
- **Prompt injection** — runbook chunks are treated as untrusted; the LLM prompt clearly separates *instructions* from *context*.
- **Audit** — every state transition is checkpointed and the compliance report is written to an immutable store.

**Q20. How do you observe/monitor this workflow in production?**
LangSmith (or OpenTelemetry) traces on every node; structured logs including `thread_id`, agent name, tool name, and latency; metrics on approval latency, remediation success rate, and validation failure rate; alerts on any workflow stuck at approval for >24h or any validation failure.

