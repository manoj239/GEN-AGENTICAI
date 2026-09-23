# Project 2 — Patch Management Automation (Patch.py)

> Source file: [14.Sample/Patch.py](Patch.py)

---

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
        | Compliance Report Agent  |
        +--------------------------+
                    |
                    v
                +-------+
                |  END  |
                +-------+

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
| `remediation_agent` | Apply patches | `state` | `remediation` = "Patches installed successfully" | — |
| `validation_agent` | Confirm services are healthy after patching | `state` | `validation` = "Services Healthy" | — |
| `compliance_agent` | Emit compliance/audit report | `state` | Log message; state unchanged | — |

---

## 10. State Management

The workflow uses a single typed state object:

```python
class PatchState(TypedDict):
    patch_data: dict
    risk_level: str
    runbook: str
    approval: str
    remediation: str
    validation: str
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

- **Single branch — approval-based:** if the human says "no", the workflow
  *stops* before any change; if "yes", it *continues* through remediation →
  validation → compliance.
- There is **no auto-retry loop** in this implementation.

---

## 12. Tool Integrations

| Tool / Service | Used By | Purpose | Input | Output |
|---|---|---|---|---|
| `get_patch_info()` (MCP) | `patch_assessment_agent` | Return missing/critical patch info | — | `{"missing_patches": 15, "critical": True}` |
| `retrieve_runbook()` (MCP / RAG) | `runbook_agent` | Return runbook / SOP for patching | — | Runbook text (apply patches, restart, validate) |
| Console `input()` | `approval_agent` | Capture human approval decision | Prompt string | `"yes"` / `"no"` |
| `MemorySaver` (LangGraph) | Graph runtime | Checkpoint workflow state | State snapshot | Persisted checkpoint |

There is no external patch execution API wired up — remediation is represented
as a status text.

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
1. What is the Supervisor pattern, and how does `supervisor_agent` differ from a
   plain orchestrator?
2. Where exactly is RAG used in this project, and why does it matter?
3. Why is the approval node placed *after* assessment, risk, and runbook — and
   not earlier?
4. What does `MemorySaver` give you here? Would you use it in production?
5. What happens if the human rejects approval? What state has been captured?
6. How is unsafe remediation prevented? (Approval gate + validation +
   compliance.)
7. How would you replace the mock `get_patch_info()` and `retrieve_runbook()`
   with real MCP servers?
8. How would you plug an actual LLM into the risk / runbook / remediation
   reasoning?
9. How would you handle a remediation failure — where would retries or a
   rollback branch go?
10. What structured outputs are you using? (`TypedDict` state fields.)
11. How would you extend the approval flow to route based on `risk_level`
    (e.g., auto-approve LOW, require HITL only for HIGH)?
12. How is this different from the Incident Management project (Langraph.py) —
    what's added here?
