# Project 1 — Incident Management Automation (Langraph.py)

> Source file: [14.Sample/Langraph.py](Langraph.py)

---

## 1. What is the Use Case?

In a typical enterprise IT operations environment, when a production service fails
(for example, an Apache web server going down), an incident is raised in ServiceNow.
An on-call engineer has to:

- Manually open the incident in ServiceNow.
- Read the short description and severity.
- Perform Root Cause Analysis (RCA).
- Decide whether remediation is required.
- Get approval from a senior engineer for any corrective action.
- Manually execute the remediation (e.g., restart the service).

This is slow, repetitive, and depends heavily on the on-call engineer's availability
and experience.

**Use case:** Automate the intake, analysis, approval, and remediation of production
incidents pulled from ServiceNow, while still keeping a human in control of any
change action.

---

## 2. What Solution Are We Implementing?

We are building an **Agentic AI workflow** using **LangGraph** where multiple
specialized agents coordinate to handle an incident end-to-end:

- An **Orchestrator** starts the workflow.
- An **Intake Agent** pulls incident data from ServiceNow via an **MCP tool**.
- An **Analysis Agent** performs RCA.
- A **conditional router** decides whether remediation is needed based on severity.
- A **Human-in-the-Loop Approval Agent** takes the go/no-go decision.
- A **Remediation Agent** executes the corrective action if approved.
- **LangGraph's MemorySaver** checkpoints state so the workflow is resumable.

**Why Agentic AI?** Because handling an incident is not a single LLM prompt — it
requires *multi-step reasoning*, *tool calling* (ServiceNow), *conditional branching*
(severity-based), *human approval*, and *stateful memory* across nodes. Those are
exactly the properties an agentic workflow provides.

---

## 3. Concept / Technology Mapping Table

| Concept | Implementation in This Project | Purpose |
|---|---|---|
| Problem | Manual triage of ServiceNow incidents | Slow, inconsistent, human-heavy |
| Agentic AI | Multi-node LangGraph workflow with specialized agents | Automate reasoning, tool use, and decisions |
| LangGraph | `StateGraph(IncidentState)` with nodes + conditional edges | Orchestrate agents as a graph |
| Architecture | Orchestrator → Intake → Analysis → (Approval → Remediation) → END | End-to-end incident automation |
| Agents | `orchestrator`, `intake_agent`, `analysis_agent`, `approval_agent`, `remediation_agent` | Divide responsibilities |
| State Management | `IncidentState` `TypedDict` | Carry incident data across nodes |
| Routing / Conditional Routing | `need_remediation`, `approval_router` | Branch on severity and approval |
| Tools / Tool Calling | `fetch_incident_from_servicenow(incident_id)` | Retrieve incident data |
| MCP | ServiceNow MCP tool call inside `intake_agent` | External system integration |
| RAG | *Not implemented in this project* | — |
| Human-in-the-Loop | `approval_agent()` using `input(...)` | Human go/no-go before remediation |
| LLM | Represented by agent nodes (RCA text produced by `analysis_agent`) | Reasoning step |
| Structured Outputs | `TypedDict` state (`IncidentState`) with typed fields | Predictable data contract |
| Validation / Safeguards | Severity gate + Human approval gate | Prevent unsafe auto-remediation |
| Persistence / Memory | `MemorySaver()` checkpointer | Resumable, durable workflow |

---

## 4. Problem

Without this system, incident handling is fully manual:

- Engineers must **log in** to ServiceNow and pull details for each incident.
- RCA is done ad-hoc, based on individual experience.
- There is **no consistent gate** for whether remediation is needed — engineers judge case by case.
- Approval is chased over chat/email, delaying MTTR.
- Remediation steps (e.g., "restart Apache") are executed manually, with no audit
  trail linking incident → analysis → approval → action.

Difficulties:

- **Slow response time** for high-severity incidents.
- **Inconsistent RCA quality** across engineers.
- **No traceability** of who approved what.
- **No resumability** — if the engineer stops mid-way, context is lost.

---

## 5. Why Agentic AI?

A single LLM call cannot handle this end-to-end. This workflow needs:

1. **Multiple steps** — fetch incident, analyze, decide, approve, remediate.
2. **Tool calling** — invoking the ServiceNow MCP tool (`fetch_incident_from_servicenow`).
3. **Conditional decisions** — routing based on `severity == "High"` and on the
   human's `yes/no` answer.
4. **State carried across steps** — `incident_data`, `analysis`, `approval`, and
   `remediation` accumulate in `IncidentState` as the workflow progresses.
5. **Human collaboration** — the approval step requires a real human decision, not
   just an LLM answer.

Agentic AI (agents + tools + state + routing) is the right pattern because each
agent has a *narrow, well-defined role* and the *graph itself* controls how those
roles are chained.

---

## 6. Why LangGraph?

LangGraph is used because the project needs an explicit, inspectable, stateful
graph of nodes and edges — not just a chain of LLM calls.

- **State management:** `StateGraph(IncidentState)` gives a single typed state
  object shared by every node.
- **Nodes as agents:** every agent (`orchestrator`, `intake`, `analysis`,
  `approval`, `remediation`) is a node.
- **Conditional edges:** `add_conditional_edges("analysis", need_remediation, ...)`
  and `add_conditional_edges("approval", approval_router, ...)` implement
  branching logic natively.
- **Human-in-the-Loop:** the approval node blocks on `input(...)` and its return
  value drives the next edge.
- **Resumability / Failure handling:** `builder.compile(checkpointer=memory)` with
  `MemorySaver()` persists state so the graph can be resumed from where it stopped.

---

## 7. Architecture

```
                +------------------+
                |       User       |
                +------------------+
                          |
                          v
                +--------------------+
                | Orchestrator Node  |
                +--------------------+
                          |
                          v
        +-------------------------------------+
        | Intake Agent                        |
        | -> fetch_incident_from_servicenow() |
        |    (ServiceNow MCP Tool)            |
        +-------------------------------------+
                          |
                          v
                +------------------+
                |  Analysis Agent  |
                |    (RCA text)    |
                +------------------+
                          |
                          v
                +---------------------+
                |  need_remediation?  |
                | severity == High ?  |
                +---------------------+
                    |            |
                 NO |            | YES
                    v            v
                +-------+   +------------------+
                |  END  |   | Approval Agent   |
                +-------+   | (Human in Loop)  |
                            +------------------+
                                     |
                                     v
                            +----------------+
                            |  approval ==   |
                            |    "yes" ?     |
                            +----------------+
                              |          |
                           YES|          |NO
                              v          v
                    +--------------------+  +-------+
                    | Remediation Agent  |  |  END  |
                    | (Restart Apache)   |  +-------+
                    +--------------------+
                              |
                              v
                          +-------+
                          |  END  |
                          +-------+

              [ MemorySaver checkpointer wraps the whole graph ]
```

Components:

- **LLM/agent nodes** — Orchestrator, Intake, Analysis, Approval, Remediation.
- **LangGraph** — the `StateGraph` connecting them.
- **State** — `IncidentState` (`TypedDict`).
- **Tool / MCP** — `fetch_incident_from_servicenow()`.
- **HITL** — `approval_agent` via console input.
- **Persistence** — `MemorySaver()`.

---

## 8. Workflow

Step-by-step:

1. **Invoke** — `graph.invoke({"incident_id": "INC1001"})`.
2. **Orchestrator node** — logs "Orchestrator Started" and passes state through.
3. **Intake node** — calls the ServiceNow MCP tool, populates
   `incident_data` = `{"short_desc": "Apache Service Down", "severity": "High"}`.
4. **Analysis node** — writes an RCA into `state["analysis"]`.
5. **Conditional edge `need_remediation`:**
   - If `severity == "High"` → route to `approval`.
   - Else → `END`.
6. **Approval node (HITL)** — prompts *"Approve remediation? (yes/no)"* and stores
   the answer in `state["approval"]`.
7. **Conditional edge `approval_router`:**
   - If `approval == "yes"` → route to `remediation`.
   - Else → `END`.
8. **Remediation node** — writes the corrective action (`"Restart Apache Service"`)
   into `state["remediation"]`.
9. **END** — final state is checkpointed via `MemorySaver`.

Decision points:

- **Severity gate** (analysis → approval | end).
- **Approval gate** (approval → remediation | end).

---

## 9. Agents

| Agent | Responsibility | Input | Output | Tools Used |
|---|---|---|---|---|
| `orchestrator` | Entry point; kicks off the workflow | `IncidentState` | Unchanged state | — |
| `intake_agent` | Pull incident details from ServiceNow | `state["incident_id"]` | `incident_data` dict | `fetch_incident_from_servicenow` (MCP) |
| `analysis_agent` | Produce RCA text | `state` | `analysis` string | — |
| `approval_agent` | Get human go/no-go | `state` | `approval` = "yes"/"no" | Console `input()` (HITL) |
| `remediation_agent` | Execute corrective action | `state` | `remediation` text ("Restart Apache Service") | — |

---

## 10. State Management

The workflow uses a single typed state object:

```python
class IncidentState(TypedDict):
    incident_id: str
    incident_data: dict
    analysis: str
    approval: str
    remediation: str
```

How information flows:

- `incident_id` is supplied at invocation.
- `intake_agent` adds `incident_data`.
- `analysis_agent` adds `analysis`.
- `approval_agent` adds `approval`.
- `remediation_agent` adds `remediation`.

Each node returns a partial dict; LangGraph merges it into the shared state, so
every downstream node sees all previous findings, decisions, and actions.

**Persistence:** `MemorySaver()` is attached via
`builder.compile(checkpointer=memory)`, so the state can be checkpointed and the
workflow resumed.

---

## 11. Routing Logic

Static edges:

- `set_entry_point("orchestrator")`
- `orchestrator → intake`
- `intake → analysis`
- `remediation → END`

Conditional edges:

1. **`need_remediation`** (after `analysis`):
   - Reads `state["incident_data"]["severity"]`.
   - `"High"` → `"approval"`.
   - Anything else → `END`.
2. **`approval_router`** (after `approval`):
   - `state["approval"] == "yes"` → `"remediation"`.
   - Anything else → `END`.

Where the workflow can branch, stop, or continue:

- **Branch #1 — severity-based:** low-severity incidents *stop* after analysis.
- **Branch #2 — approval-based:** if the human says "no", the workflow *stops*
  before any change action; if "yes", it *continues* to remediation.

There is **no auto-retry loop** in this implementation — routes lead to either
the next node or `END`.

---

## 12. Tool Integrations

| Tool / Service | Used By | Purpose | Input | Output |
|---|---|---|---|---|
| ServiceNow MCP (`fetch_incident_from_servicenow`) | `intake_agent` | Fetch incident short description and severity | `incident_id: str` | `{"short_desc": ..., "severity": ...}` |
| Console `input()` | `approval_agent` | Capture human approval decision | Prompt string | `"yes"` / `"no"` |
| `MemorySaver` (LangGraph) | Graph runtime | Checkpoint workflow state for resumability | State snapshot | Persisted checkpoint |

No RAG store, no LLM API, and no external remediation API are wired up in this
file — remediation is represented as a text action.

---

## 13. Human-in-the-Loop / Safety Controls

Human approval is enforced by `approval_agent`:

- Triggered **only for High-severity** incidents (severity gate in
  `need_remediation`).
- Blocks on `input("Approve remediation? (yes/no): ")`.
- If the answer is `"yes"` → `remediation_agent` runs.
- If the answer is anything else → routed to `END`, and no action is taken.

Safeguards separating investigation from operational remediation:

- The **Analysis Agent** only *describes* the RCA — it does not change anything.
- The **Remediation Agent** is the only node that represents a change action, and
  it can only be reached *after* both the severity gate and the human approval
  gate pass.

---

## 14. End-to-End Solution Design

```
Input: {"incident_id": "INC1001"}
      |
      v
LangGraph Workflow (StateGraph + MemorySaver)
      |
      v
Agents: Orchestrator -> Intake -> Analysis -> Approval -> Remediation
      |
      v
State: IncidentState (incident_id, incident_data, analysis, approval, remediation)
      |
      v
Routing / Decisions:
   - need_remediation (severity == "High")
   - approval_router  (approval == "yes")
      |
      v
Tools: ServiceNow MCP tool (fetch_incident_from_servicenow)
      |
      v
Human Approval: approval_agent (blocking input)
      |
      v
Remediation / Final Action: "Restart Apache Service" text
      |
      v
Persistence / Reporting: MemorySaver checkpoints final state
```

---

## 15. Business Value

Based on what is actually implemented:

- **Reduced manual effort** — engineers no longer manually pull incidents,
  analyze, and chase approvals.
- **Faster investigation** — analysis is triggered automatically right after
  intake.
- **Consistency** — every incident goes through the same nodes in the same order.
- **Safety** — a change action (remediation) can only happen after a severity
  check *and* an explicit human approval.
- **Auditability** — state (`incident_data`, `analysis`, `approval`,
  `remediation`) is captured and checkpointed via `MemorySaver`.
- **Resumability** — if the workflow is interrupted (e.g., during approval), it
  can be resumed from the last checkpoint.

---

## 16. Interview Explanation

### 30-second explanation
> I built an incident management workflow in LangGraph. It pulls a ServiceNow
> incident via an MCP tool, an analysis agent does RCA, and a conditional edge
> checks severity. If it's high, it goes to a human approval node; only if the
> human says yes does the remediation agent run. State is kept in a `TypedDict`
> and persisted with `MemorySaver`.

### 1-minute explanation
> The project automates production incident handling. The entry point is an
> orchestrator node. The next node is an intake agent that calls a ServiceNow MCP
> tool (`fetch_incident_from_servicenow`) and stores the returned incident data in
> the LangGraph state. An analysis agent then produces an RCA. After that, a
> conditional edge (`need_remediation`) checks severity — if it's `"High"`, the
> graph routes to a human approval node; otherwise it ends. The approval node
> blocks on a console `input()` and stores `"yes"`/`"no"` in state. A second
> conditional edge routes to a remediation agent only when the answer is `"yes"`.
> The whole graph is compiled with a `MemorySaver` checkpointer, so state is
> durable and the workflow is resumable.

### 2-minute detailed explanation
> The problem I'm solving is that ServiceNow incidents are handled manually —
> engineers pull the ticket, do RCA, chase approvals, and then execute a
> remediation like restarting Apache. I automated this with an Agentic AI workflow
> in LangGraph.
>
> The state is an `IncidentState` `TypedDict` with `incident_id`, `incident_data`,
> `analysis`, `approval`, and `remediation`. I built a `StateGraph` around it and
> added five nodes: `orchestrator`, `intake_agent`, `analysis_agent`,
> `approval_agent`, and `remediation_agent`. The orchestrator is the entry point
> and just kicks off the flow. The intake agent calls the ServiceNow MCP tool
> `fetch_incident_from_servicenow` and writes the short description and severity
> into state. The analysis agent writes an RCA string.
>
> Then there are two conditional edges. The first, `need_remediation`, reads the
> severity from state; if it's `"High"` it routes to the approval node, otherwise
> it goes to `END`. The approval node is Human-in-the-Loop — it prompts the
> engineer for `yes/no`. The second conditional edge, `approval_router`, checks
> that answer: `"yes"` routes to the remediation agent, anything else routes to
> `END`. The remediation agent writes the action ("Restart Apache Service") into
> state.
>
> I compiled the graph with `MemorySaver` as the checkpointer, which gives me
> durable state and resumability. So this pattern gives me multi-agent
> orchestration, tool calling via MCP, conditional routing on severity and
> approval, HITL safety, and a persistent audit trail — all the properties you
> want for enterprise incident automation.

### Important follow-up questions an interviewer may ask
1. Why LangGraph instead of a simple `if/else` script or a plain LangChain chain?
2. What exactly does the `MemorySaver` checkpointer buy you here?
3. How is the ServiceNow MCP tool wired in — is it a real MCP client or a stub?
4. What happens if the human never responds to the approval prompt?
5. Where would you plug in a real LLM for RCA, and why isn't one used today?
6. How would you add retries or failure handling if the ServiceNow call fails?
7. How is unsafe remediation prevented? (Severity gate + approval gate.)
8. How would you extend this to multiple severities (e.g., Medium)?
9. How would you replace the console `input()` HITL with a real UI/Slack/Teams approval?
10. How is state passed between nodes, and what does each node return?
11. Where would RAG fit in this workflow if you wanted it?
12. How would you scale this to handle many incidents in parallel?
