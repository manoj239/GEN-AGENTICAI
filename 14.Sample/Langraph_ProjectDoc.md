# Project 1 — Incident Management Automation (Langraph.py)

---

## 1. What is the Use Case?

In enterprise IT operations, production incidents (a VM going unhealthy, a
server unreachable, a network device down, an application service failing) are
raised in ServiceNow and handled by an on-call engineer. Every incident goes
through the same manual routine: pull the ticket, run diagnostic commands
(ping, SSH, router status), collect logs, look at historical health, search
runbooks/SOPs/KB/SharePoint for the fix, chase an approval, and then execute
the remediation.

**This project automates that end-to-end** — from incident intake to gated
remediation — while keeping a human in control of any change action. The POC
uses an Excel file as the incident source; in production the same Triage Agent
reads from ServiceNow.

---

## 2. What Solution Are We Implementing?

A **LangGraph multi-agent workflow** with **five specialized agents**:

1. **Triage Agent** — retrieves the incident (Excel in POC, ServiceNow in prod).
2. **Command Executor & Log Extractor Agent** — runs initial diagnostic checks
   based on incident type (e.g., ping, SSH connectivity, switch/router status)
   and collects relevant logs and command output.
3. **Diagnostic Agent** — analyzes historical and current health of the affected
   VM / server / network device.
4. **RCA / Analysis Agent** — retrieves troubleshooting and resolution steps
   from Runbooks / SOPs / KB / SharePoint using RAG.
5. **Remediation Agent** — executes the recommended remediation, gated by a
   Human-in-the-Loop approval.

The graph is compiled with LangGraph's `MemorySaver` so state is checkpointed
and the workflow is resumable — important because HITL can pause it
indefinitely. Agentic AI is used because incident handling is inherently
multi-step: it requires several tool calls, RAG-grounded reasoning, conditional
branching, human approval, and shared state across agents — none of which a
single LLM prompt can do.

---

## 3. Concept / Technology Mapping Table

| Concept | Implementation in This Project | Purpose |
|---|---|---|
| Problem | Manual triage, diagnostics, RCA lookup and remediation of incidents; fragmented tools + knowledge; no audit trail | Baseline pain the project fixes |
| Agentic AI | 5 specialized agents chained through a LangGraph `StateGraph` | Multi-step reasoning + tool use + decisions |
| LangGraph | `StateGraph(IncidentState)`, `add_node`, `add_edge`, `add_conditional_edges`, `MemorySaver` | Orchestration + branching + persistence |
| Architecture | Triage → Cmd/Log → Diagnostic → RCA → (gate) → Remediation (HITL) → (gate) → Execute | Sequential agents with 2 safety gates |
| Agents | Triage, Command Executor & Log Extractor, Diagnostic, RCA/Analysis, Remediation | Each agent owns one narrow responsibility |
| State Management | `IncidentState` (`TypedDict`) shared across all nodes | One typed context object carrying findings |
| Routing / Conditional Routing | `need_remediation` (severity/RCA gate) and `approval_router` (HITL gate) | Branch on state and human decision |
| Tools / Tool Calling | Excel reader / ServiceNow, ping, SSH check, switch/router status, log extractor, change executor | Intake + diagnostics + execution |
| MCP | ServiceNow fetch exposed as an MCP tool (`fetch_incident_from_servicenow` in POC) | Standardized external integration |
| RAG | Runbooks / SOPs / KB / SharePoint retrieved by the RCA Agent | Ground recommendations in approved procedures |
| Human-in-the-Loop | Approval step inside the Remediation Agent | No change without an explicit human `yes` |
| LLM | Reasoning inside Diagnostic + RCA / Analysis agents | Health analysis + RCA + step selection |
| Structured Outputs | Typed fields of `IncidentState` | Predictable data contract between agents |
| Safeguards | Read-only investigation agents + 2 conditional gates + RAG grounding | Prevent unsafe or hallucinated remediation |
| Persistence / Memory | `MemorySaver()` checkpointer wrapping the compiled graph | Resumability + audit trail |

*(Section 4 “Problem” was intentionally merged into the "Problem" row above to
avoid repeating the same bullets.)*

---

## 5. Why Agentic AI?

A single LLM call cannot handle this — the workflow is multi-step, multi-tool,
and involves real decisions and a human.

- **Multiple specialized steps.** Triage, diagnostic execution, log/health
  analysis, RCA lookup and remediation are logically distinct; each needs its
  own prompt, tools, and error handling.
- **Real tool calls.** ServiceNow / Excel intake, ping, SSH connectivity,
  switch/router status, and log extractors are external actions, not language.
- **RAG-grounded reasoning.** The RCA / Analysis agent must retrieve
  troubleshooting steps from runbooks / SOPs / KB / SharePoint so
  recommendations are grounded, not hallucinated.
- **Conditional execution.** Two decisions drive the flow — *does this incident
  need remediation?* and *did the human approve?*.
- **Shared state.** Each agent produces findings (incident data, logs, health,
  RCA, approval, remediation result) that later agents must consume.
- **Human collaboration.** No LLM should trigger a production change on its
  own; a human explicitly approves.

Agentic AI (agents + tools + state + routing + HITL) is the natural fit.

---

## 6. Why LangGraph?

LangGraph was chosen because it gives an explicit, inspectable, stateful graph
that maps directly to the 5-agent design.

- **Typed shared state** — `StateGraph(IncidentState)` gives every agent the
  same `TypedDict` context. Each agent returns a partial dict, LangGraph merges
  it. That's how findings flow from Triage → Cmd/Log → Diagnostic → RCA →
  Remediation without any custom plumbing.
- **Nodes = agents** — each of the 5 agents is a node registered via
  `add_node`, so the graph is easy to visualize and audit.
- **Conditional edges** — `add_conditional_edges` implements the two gates
  (`need_remediation`, `approval_router`) natively; no manual `if/else`
  scaffolding.
- **HITL support** — the approval step blocks the graph until the human
  responds, and the answer drives the next edge.
- **`MemorySaver` checkpointer** — `builder.compile(checkpointer=MemorySaver())`
  persists state between steps, so a workflow paused at HITL or interrupted
  mid-run can resume from the last checkpoint.
- **Failure handling** — because state is checkpointed and every node returns
  a partial update, a failing tool call can be retried without re-running the
  earlier agents.

---

## 7. Architecture

```
                +------------------+
                |       User       |
                +------------------+
                          |
                          v
        +--------------------------------------+
        |            Triage Agent              |
        |   POC: Excel  /  Prod: ServiceNow    |
        +--------------------------------------+
                          |
                          v
        +--------------------------------------+
        | Command Executor & Log Extractor     |
        |  ping / SSH / switch-router status / |
        |            log collection            |
        +--------------------------------------+
                          |
                          v
        +--------------------------------------+
        |          Diagnostic Agent            |
        |  historical + current health of the  |
        |    VM / server / network device      |
        +--------------------------------------+
                          |
                          v
        +--------------------------------------+
        |         RCA / Analysis Agent         |
        |   RAG: Runbooks / SOPs / KB /        |
        |             SharePoint               |
        +--------------------------------------+
                          |
                          v
                +---------------------+
                |  Need Remediation?  |
                +---------------------+
                    |            |
                 NO |            | YES
                    v            v
                +-------+   +--------------------------+
                |  END  |   |     Remediation Agent    |
                +-------+   |     (Human in Loop)      |
                            +--------------------------+
                                       |
                                       v
                            +----------------------+
                            |  approval == "yes"?  |
                            +----------------------+
                              |            |
                           YES|            |NO
                              v            v
                    +--------------------+  +-------+
                    | Execute Remediation|  |  END  |
                    +--------------------+  +-------+
                              |
                              v
                          +-------+
                          |  END  |
                          +-------+

              [ MemorySaver checkpointer wraps the whole graph ]
```

**Major components:** LangGraph `StateGraph`, `IncidentState` (`TypedDict`),
five agents (LLM-powered nodes), MCP tools (ServiceNow / Excel intake, ping,
SSH, router status, log extractor), a RAG store over runbooks/SOPs/KB/SharePoint,
a HITL approval step inside the Remediation Agent, and `MemorySaver` for
persistence.

---

## 8. Workflow

1. **Invoke** — `graph.invoke({"incident_id": "INC1001"})`.
2. **Triage Agent** — fetches the incident (Excel in POC / ServiceNow in prod)
   and writes `incident_data` (short description, severity, type, affected
   asset) into state.
3. **Command Executor & Log Extractor Agent** — based on incident type, runs
   diagnostic checks (for a network incident: ping, SSH connectivity,
   switch/router status) and collects logs / command output into state.
4. **Diagnostic Agent** — analyzes historical + current health of the affected
   asset and writes a health analysis into state.
5. **RCA / Analysis Agent** — retrieves troubleshooting and resolution steps
   from Runbooks / SOPs / KB / SharePoint (RAG) and writes RCA +
   recommended_steps into state.
6. **Decision — need remediation?**
   - **No** → graph goes to `END`.
   - **Yes** → route to the Remediation Agent.
7. **Remediation Agent (HITL)** — presents the incident, RCA and recommended
   steps to the human and asks for approval.
8. **Decision — approval?**
   - **`"yes"`** → executes the recommended steps and writes `remediation` into
     state.
   - **anything else** → `END`, no change is applied.
9. **End** — final state is checkpointed by `MemorySaver` (audit trail).

Decision points: (a) severity / need-remediation gate after RCA, (b) HITL
approval gate inside Remediation.

---

## 9. Agents

| Agent | Responsibility | Input | Output | Tools Used |
|---|---|---|---|---|
| **Triage Agent** | Retrieve incident details | `incident_id` | `incident_data` (desc, severity, type, asset) | Excel reader (POC) / ServiceNow MCP (`fetch_incident_from_servicenow`) |
| **Command Executor & Log Extractor** | Initial diagnostic checks + log collection based on incident type | `incident_data` | `diagnostic_output`, `logs` | ping, SSH connectivity check, switch/router status check, log extractor |
| **Diagnostic Agent** | Historical + current health analysis of affected asset | `incident_data`, `diagnostic_output`, `logs` | `health_analysis` | Monitoring / historical health data lookup |
| **RCA / Analysis Agent** | Retrieve troubleshooting + resolution steps | full state | `rca`, `recommended_steps` | RAG over Runbooks / SOPs / KB / SharePoint |
| **Remediation Agent** | HITL approval + execute recommended remediation | `rca`, `recommended_steps` | `approval`, `remediation` | HITL prompt + change / execution tool |

---

## 10. State Management

The workflow uses a single typed state object, `IncidentState` (a `TypedDict`).
Each agent returns a partial dict and LangGraph merges it into the shared
state, so every downstream agent sees all previous findings.

Fields accumulated across the flow:

- `incident_id` — supplied at invocation.
- `incident_data` — from **Triage** (short desc, severity, type, affected
  asset).
- `diagnostic_output`, `logs` — from **Command Executor & Log Extractor**.
- `health_analysis` — from **Diagnostic**.
- `rca` / `recommended_steps` — from **RCA / Analysis** (RAG-grounded).
- `approval` — from **Remediation** (HITL answer).
- `remediation` — from **Remediation** after execution.

The POC uses a smaller `IncidentState` (`incident_id`, `incident_data`,
`analysis`, `approval`, `remediation`); the real design extends the same
pattern with the fields above.

**Persistence:** `builder.compile(checkpointer=MemorySaver())` checkpoints the
state after each node, giving resumability (critical while paused at HITL) and
an audit trail of every decision.

---

## 11. Routing Logic

**Static edges** (fixed sequence between agents):

- Entry point → **Triage Agent**
- Triage → **Command Executor & Log Extractor**
- Cmd/Log → **Diagnostic**
- Diagnostic → **RCA / Analysis**

**Conditional edges (2 gates):**

1. **`need_remediation`** — evaluated after RCA:
   - If remediation is not required → `END`.
   - If required → route to the **Remediation Agent**.
   - In the POC this is implemented by reading
     `state["incident_data"]["severity"]` and returning `"approval"` for
     `"High"` or `"end"` otherwise.
2. **`approval_router`** — evaluated inside the Remediation Agent:
   - `state["approval"] == "yes"` → execute the recommended steps.
   - Otherwise → `END`, no change is applied.

**Branch points, stop points, and safety:**

- Informational incidents *stop* after RCA (no unnecessary change action).
- A `"no"` from the human *stops* the workflow before any change is executed.
- Every execute path is preceded by both gates, so no auto-remediation is
  possible.
- There is no auto-retry loop — routes lead to either the next node or `END`.

---

## 12. Tool Integrations

| Tool / Service | Used By | Purpose | Input | Output |
|---|---|---|---|---|
| Excel reader (POC) / ServiceNow MCP (prod) | Triage Agent | Fetch incident details | `incident_id` | `incident_data` (desc, severity, type, asset) |
| Ping | Command Executor & Log Extractor | Basic network reachability | Target host/IP | Reachability result |
| SSH connectivity check | Command Executor & Log Extractor | Verify server access | Host + credentials/session | Session status |
| Switch / router status check | Command Executor & Log Extractor | Verify network device state | Device identifier | Device status |
| Log Extractor | Command Executor & Log Extractor | Collect relevant logs | Asset + time range | Log snippets |
| Monitoring / historical health lookup | Diagnostic Agent | Past + current health of affected asset | Asset id | Health analysis |
| RAG store (Runbooks / SOPs / KB / SharePoint) | RCA / Analysis Agent | Retrieve troubleshooting + resolution steps | Incident context + health analysis | Grounded RCA + recommended steps |
| HITL prompt | Remediation Agent | Capture human approval | Approval prompt (with context) | `"yes"` / `"no"` |
| Change / execution tool | Remediation Agent | Apply the recommended remediation | Recommended steps | Execution result |
| `MemorySaver` (LangGraph) | Graph runtime | Checkpoint workflow state | State snapshot | Persisted checkpoint |

---

## 13. Human-in-the-Loop / Safety Controls

Human approval is enforced **inside the Remediation Agent** and is the only
gate that can trigger a real change.

- The Remediation Agent is reached only when the `need_remediation` gate says
  remediation is required.
- The human sees the full accumulated state — incident details, diagnostic
  output, logs, health analysis, and the RCA with recommended steps — before
  deciding.
- `"yes"` → the recommended steps execute.
- Anything else → routed to `END`; no change is applied.

**Separation of investigation from operational remediation:**

- **Triage**, **Command Executor & Log Extractor**, **Diagnostic**, and **RCA /
  Analysis** are read-only / informational — they cannot modify the target
  system.
- **Remediation** is the only agent that performs a change action, and it can
  only execute after both the `need_remediation` gate and the HITL gate pass.
- Because the RCA / Analysis agent uses RAG over Runbooks / SOPs / KB /
  SharePoint, the steps presented to the human are grounded in approved
  procedures — not freeform LLM output.

---

## 14. End-to-End Solution Design

```
Input: incident_id
   │
   ▼
LangGraph Workflow (StateGraph + MemorySaver)
   │
   ▼
Agents:  Triage
      → Command Executor & Log Extractor
      → Diagnostic
      → RCA / Analysis
      → Remediation (HITL)
   │
   ▼
State: IncidentState
       (incident_id, incident_data, diagnostic_output, logs,
        health_analysis, rca / recommended_steps, approval, remediation)
   │
   ▼
Routing / Decisions:
   - need_remediation ?
   - approval == "yes" ?
   │
   ▼
Tools / RAG / APIs:
   - Excel / ServiceNow MCP (Triage)
   - ping / SSH / router status / log extractor (Cmd/Log)
   - Monitoring / historical health (Diagnostic)
   - RAG: Runbooks / SOPs / KB / SharePoint (RCA)
   - Change / execution tool (Remediation)
   │
   ▼
Human Approval: inside Remediation Agent
   │
   ▼
Remediation / Final Action: recommended steps executed
   │
   ▼
Reporting / Audit: MemorySaver checkpoints final state
```

---

## 15. Business Value

- **Reduced manual effort** — engineers no longer manually pull incidents, run
  diagnostic commands, chase runbooks, or copy-paste RCA steps.
- **Faster investigation / lower MTTR** — Triage → Cmd/Log → Diagnostic → RCA
  runs automatically with shared state; the human only needs to approve.
- **Consistency** — every incident goes through the same five agents in the
  same order, regardless of who is on call.
- **Operational safety** — read-only investigation agents plus two conditional
  gates ensure no change happens without human approval.
- **Standardization** — RCA is RAG-grounded in Runbooks / SOPs / KB /
  SharePoint, not ad-hoc engineer memory.
- **Auditability** — `IncidentState` captures incident data, diagnostics,
  logs, health analysis, RCA, approval, and remediation; `MemorySaver`
  checkpoints every step.
- **Resumability** — the workflow can pause indefinitely at HITL and resume
  from the last checkpoint without losing context.

---

## 16. Interview Explanation

### 30-second explanation
> I built a five-agent LangGraph workflow for production incidents. A Triage
> Agent pulls the ticket (Excel in POC, ServiceNow in prod). A Command Executor
> & Log Extractor Agent runs ping / SSH / router checks and collects logs. A
> Diagnostic Agent analyzes historical and current health. An RCA / Analysis
> Agent uses RAG over runbooks / SOPs / KB / SharePoint. A Remediation Agent
> executes the fix only after a Human-in-the-Loop approval. State is a typed
> `IncidentState` shared across agents; `MemorySaver` gives resumability.

### 1-minute explanation
> The workflow starts with a **Triage Agent** that fetches incident details —
> Excel in POC, ServiceNow in production. A **Command Executor & Log Extractor
> Agent** runs initial diagnostic checks per incident type — for network
> incidents that's ping, SSH connectivity and switch/router status — and
> collects logs. A **Diagnostic Agent** looks at historical and current health
> of the affected VM/server/network device. An **RCA / Analysis Agent** does
> RAG over runbooks, SOPs, KB and SharePoint to fetch resolution steps
> grounded in approved procedures. A conditional edge (`need_remediation`)
> then decides if remediation is needed; if yes, the **Remediation Agent**
> presents the RCA and steps and asks a human for approval. Only on `"yes"`
> does it execute the steps; otherwise the workflow ends. Everything runs on
> a LangGraph `StateGraph` with `MemorySaver`, so state is durable and the
> graph can resume — critical because it pauses at HITL.

### 2-minute explanation
> The problem is that production incidents are handled manually today.
> Engineers pull the ticket from ServiceNow, run diagnostic commands, look at
> monitoring, search runbooks or SharePoint for the fix, chase approvals, and
> execute remediation by hand. That's slow, inconsistent, and unauditable.
>
> I built an Agentic AI workflow in LangGraph with five agents.
>
> **Triage Agent** fetches incident details — Excel for the POC, ServiceNow
> (as an MCP tool) in production — and writes them into a typed
> `IncidentState`.
>
> **Command Executor & Log Extractor Agent** runs initial diagnostics based on
> incident type. For a network incident, that's ping, SSH connectivity,
> switch/router status. It also collects logs and command output.
>
> **Diagnostic Agent** analyzes historical and current health of the affected
> asset using past operational data.
>
> **RCA / Analysis Agent** is the RAG step — it retrieves troubleshooting
> steps from runbooks, SOPs, knowledge base, and SharePoint. This grounds RCA
> in approved procedures rather than freeform LLM output.
>
> **Remediation Agent** is the only agent that changes anything. It has a
> Human-in-the-Loop approval — if the human says `"yes"`, the recommended
> steps execute; if not, the workflow stops.
>
> Two conditional edges enforce safety: a **`need_remediation`** gate after
> RCA, and an **`approval_router`** gate inside Remediation. Investigation
> agents (Triage, Cmd/Log, Diagnostic, RCA) are read-only; only Remediation
> can act. The graph is compiled with `MemorySaver`, so state is checkpointed
> and the flow can resume — important because it pauses at HITL.
>
> The result: end-to-end automation, RAG-grounded RCA, HITL safety, and a full
> audit trail in state.

### Likely interviewer follow-ups
1. Why five agents and not one? How did you decide the split?
2. How does Triage differ between POC (Excel) and production (ServiceNow)?
3. How does the Command Executor choose which diagnostic checks to run per
   incident type?
4. What's your RAG stack — sources, embeddings, vector store, refresh strategy?
5. Why is HITL inside the Remediation Agent rather than a separate node?
6. What happens on rejection? What state is preserved?
7. How would you handle failures (SSH fails, RAG empty, execution errors)?
8. How is unsafe or hallucinated remediation prevented?
9. Why LangGraph over LangChain or a plain orchestration script?
10. What does `MemorySaver` give you? Would you swap it for a persistent
    checkpointer in production?
11. How would you scale this to many incidents in parallel?
12. How does this project differ from your Patch Management project?
