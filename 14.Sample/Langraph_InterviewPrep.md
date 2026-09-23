# Incident Management Automation — Interview Prep

---

## 1. Project Overview

**Project Name:** Incident Management Automation with LangGraph.

**Business Problem**
Production incidents (VM unhealthy, server unreachable, network device down,
application service failing) are raised in ServiceNow and handled manually by
on-call engineers. Every incident goes through the same manual routine —
pulling the ticket, running diagnostics, correlating logs, looking at
historical health, searching runbooks/SOPs/KB/SharePoint, chasing approval,
and finally executing the fix.

**Why the project was needed**

- To reduce Mean Time To Resolve (MTTR).
- To make triage, diagnostics and RCA consistent across engineers.
- To ground remediation in approved runbooks instead of tribal knowledge.
- To keep an auditable trail of every incident's investigation, decision, and
  action.
- To let humans focus on the *approval decision*, not on the mechanical steps.

**Existing challenges (without this system)**

- Manual pull of incidents from ServiceNow.
- Ad-hoc diagnostic commands (ping, SSH, router status) with no consistency.
- Fragmented knowledge across Runbooks / SOPs / KB / SharePoint.
- Approvals chased over chat/email → delays MTTR.
- No audit trail linking incident → diagnostics → RCA → approval → action.
- No resumability if the on-call engineer is interrupted.

**Proposed solution**
A **LangGraph multi-agent workflow** with **five specialized agents** —
Triage, Command Executor & Log Extractor, Diagnostic, RCA / Analysis, and
Remediation — chained through a typed `IncidentState` and gated by two
conditional edges (need-remediation + HITL approval). `MemorySaver` provides
checkpointing for resumability and audit.

---

## 2. Why This Solution?

**Why this architecture was chosen**
The problem is naturally a sequence of specialized steps where each step
produces findings the next step needs. That maps directly to a **stateful,
inspectable graph of agents** — which is exactly what LangGraph provides.
Splitting the flow into five agents means each has one narrow responsibility,
which makes prompts, tools, and error handling simple.

**Why traditional approaches were insufficient**

- **Plain scripts** — hard-code decisions, no shared state, no HITL pause/
  resume, no audit checkpoints.
- **Ticket-based automation (ITSM workflow only)** — no LLM reasoning, no RAG
  grounding, no dynamic tool selection per incident type.
- **A single LLM chain** — cannot pause for human approval mid-flow, cannot
  route conditionally on real system state, and mixes investigation with
  action in a way that's unsafe.
- **A single monolithic agent** — poor observability, one giant prompt, hard
  to test and iterate.

**Why Agentic AI was needed**
Incident handling requires multiple tool calls (ServiceNow, ping, SSH, router,
logs), retrieved knowledge (runbooks/SOPs via RAG), conditional decisions
(*need remediation? approved?*), and a real human in the loop. That's a
textbook agentic workload.

**Why RAG was needed**
Resolution steps must come from **approved** procedures — runbooks, SOPs,
knowledge base, SharePoint. Freeform LLM output is unsafe for production
remediation. RAG retrieves the right procedure and grounds the RCA / Analysis
agent's recommendations.

> ⚠️ **Implementation status:** RAG is part of the design; the POC file
> `Langraph.py` does **not** implement a vector store or retrieval — the
> `analysis_agent` returns a hardcoded RCA string. See §7.

---

## 3. Technology Stack

| Component | Technology | Why Used |
| :--- | :--- | :--- |
| **Multi-Agent Orchestration** | **LangGraph** (`StateGraph`, `add_node`, `add_edge`, `add_conditional_edges`) | Enables explicit workflow orchestration with stateful agent execution and conditional routing between Triage, Cmd/Log, Diagnostic, RCA, and Remediation agents. |
| **Shared State Management** | **Python `TypedDict`** (`IncidentState`) | Provides a strongly typed state object for passing incident data, diagnostic output, logs, health analysis, RCA, approval, and remediation across agents. |
| **Persistence / Checkpointing** | **LangGraph `MemorySaver`** (`langgraph.checkpoint.memory.MemorySaver`) | Persists workflow state and allows recovery or continuation during Human-in-the-Loop interruptions or tool failures. |
| **Human-in-the-Loop** | **Console `input()`** (POC) | Introduces manual approval before any remediation or operational action, keeping a human in control of every change. |
| **Incident Intake (POC)** | **Excel file** *(designed)* / Python stub `fetch_incident_from_servicenow` *(implemented)* | Source of incident details for the POC; simulates the production ServiceNow feed so the graph can be exercised end-to-end. |
| **Incident Intake (Prod)** | **ServiceNow** (planned as an MCP tool) | Standardized integration to fetch live incidents in production through a shared tool interface. |
| **Diagnostic Tools** | **ping / SSH check / switch-router status check / log extractor** *(designed, not in POC)* | Executes initial diagnostic actions per incident type and collects command output and logs into shared state. |
| **Health Analysis** | **Monitoring / historical health lookup** *(designed)* | Analyzes past and current health of the affected VM / server / network device to explain behavior before the incident. |
| **RAG Store** | **Runbooks / SOPs / Knowledge Base / SharePoint** *(designed; not in POC)* | Grounds RCA and remediation recommendations in approved procedures instead of freeform LLM output. |
| **LLM** | *Not wired in the POC*; would sit inside the Diagnostic and RCA / Analysis agents | Provides reasoning over logs, health data, and retrieved runbook chunks to produce RCA and recommended steps. |
| **Language / Runtime** | **Python 3** | Language for the LangGraph app, agents, tool wrappers, and state definitions. |

---

## 4. Architecture

```
                +------------------+
                |   User / Ticket  |
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
        |    RAG: Runbooks / SOPs / KB /       |
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


## 5. Complete Workflow

1. **User Input** — `graph.invoke({"incident_id": "INC1001"})`.
2. **Triage Agent** reads the incident (Excel in POC / ServiceNow in prod) and
   writes `incident_data` (short desc, severity, type, affected asset) into
   state.
3. **Command Executor & Log Extractor Agent** runs diagnostic checks selected
   by incident type — for a network incident: ping, SSH connectivity check,
   switch/router status check — and collects logs / command output into state.
4. **Diagnostic Agent** analyzes historical + current health of the affected
   asset and writes `health_analysis` into state.
5. **RCA / Analysis Agent** retrieves troubleshooting and resolution steps via
   RAG over Runbooks / SOPs / KB / SharePoint, writes `rca` +
   `recommended_steps` into state.
6. **Decision 1 — `need_remediation`** (conditional edge):
   - If remediation is not required → `END`.
   - Else → route to the Remediation Agent.
7. **Remediation Agent (HITL)** presents the incident, RCA and recommended
   steps to the human and asks for approval.
8. **Decision 2 — `approval_router`** (conditional edge):
   - `state["approval"] == "yes"` → execute recommended steps, write
     `remediation` into state.
   - Otherwise → `END` without any change.
9. **End** — final state is checkpointed via `MemorySaver` (audit trail).

**Routing / decision points:**
- Severity / need-remediation gate after RCA.
- HITL approval gate inside Remediation.
- No auto-retry loop in the current implementation.

---

## 6. Agents

| Agent | Responsibility | Input | Output | Tools Used |
| :--- | :--- | :--- | :--- | :--- |
| **Triage Agent** | Retrieves the incident and normalizes its details into shared state. Reads from Excel in the POC and from ServiceNow in production. | `incident_id` | `incident_data` (short description, severity, incident type, affected asset) | **Excel reader** (POC) / **ServiceNow MCP** (prod) |
| **Command Executor & Log Extractor** | Runs initial diagnostic checks selected by incident type (ping, SSH check, switch/router status check for network incidents) and collects relevant logs and command output. | `incident_data` | `diagnostic_output`, `logs` | **ping**, **SSH check**, **switch/router status check**, **log extractor** |
| **Diagnostic Agent** | Analyzes historical and current health of the affected VM / server / network device to establish baseline behavior and detect deviations before the incident. | `incident_data`, `diagnostic_output`, `logs` | `health_analysis` | **Monitoring / historical health data lookup** |
| **RCA / Analysis Agent** | Retrieves troubleshooting and resolution steps from approved sources via RAG and produces a grounded RCA plus recommended remediation steps. | Full accumulated state | `rca`, `recommended_steps` | **RAG** over Runbooks / SOPs / Knowledge Base / SharePoint |
| **Remediation Agent** | Holds the Human-in-the-Loop approval gate and executes the recommended remediation only when the human approves. Otherwise the workflow stops without any change. | `rca`, `recommended_steps` | `approval`, `remediation` | **HITL prompt** + **change / execution tool** |

*(POC parity: the 5 agents map to `intake_agent` → Triage,
`analysis_agent` → RCA, and `approval_agent` + `remediation_agent` → the
Remediation Agent's HITL + execute steps. Cmd/Log and Diagnostic agents are
part of the design but not present in the POC file.)*

---

## 7. RAG Implementation


**Ingestion**
- Sources: Runbooks, SOPs, Knowledge Base articles, SharePoint pages.
- Loaders per source type (PDF, DOCX, HTML, SharePoint API).
- Metadata captured: source, doc id, section, incident type, asset type,
  last-updated timestamp.

**Chunking**
- Text-splitter per doc type (recursive character or section-aware for
  runbooks).
- Typical target: 500–1000 tokens with 10–15% overlap.
- Keep procedure steps in the same chunk when possible.

**Embeddings**
- A production-grade embedding model (e.g., OpenAI `text-embedding-3-*` or an
  in-house model).
- Store embeddings alongside metadata.

**Vector Database**
- Any managed or self-hosted store (e.g., PGVector, FAISS, Pinecone,
  Elastic/OpenSearch).
- Not chosen in the POC.

**Retrieval**
- Query built from `incident_data` + `health_analysis` (asset type, incident
  type, symptoms, key log lines).
- Top-k semantic search filtered by metadata (e.g., matching asset type or
  service).

**Reranking**
- Cross-encoder reranker to lift the most relevant runbook chunk to the top
  before the LLM composes the RCA.
- Optional in POC; recommended in production.

**Hybrid retrieval (optional)**
- BM25 + dense retrieval to catch exact runbook titles and command-name
  matches that pure dense retrieval can miss.

**Retrieval architecture (target):**

```
incident_data + health_analysis + key log lines
        │
        ▼
     Query builder
        │
        ▼
 ┌───────────────┐   ┌───────────────┐
 │ BM25 (hybrid) │ + │ Dense vector  │
 └───────────────┘   └───────────────┘
        │                    │
        └─────────┬──────────┘
                  ▼
             Fusion / Rerank
                  ▼
        Top runbook / SOP chunks
                  ▼
     RCA / Analysis Agent (LLM)
                  ▼
     rca + recommended_steps in state
```

---

## 8. LangGraph Implementation

**State**
- `IncidentState` is a `TypedDict` — the single object passed between nodes.
- **POC fields:** `incident_id`, `incident_data`, `analysis`, `approval`,
  `remediation`.
- **Extended (real design):** adds `diagnostic_output`, `logs`,
  `health_analysis`, `rca`, `recommended_steps`.
- Each node returns a **partial dict**, which LangGraph merges into state so
  all downstream nodes see prior findings.

**Nodes**
- POC: `orchestrator`, `intake_agent`, `analysis_agent`, `approval_agent`,
  `remediation_agent`.
- Real design: `Triage`, `Command Executor & Log Extractor`, `Diagnostic`,
  `RCA / Analysis`, `Remediation`.

**Edges**
- Static: entry → Triage → Cmd/Log → Diagnostic → RCA.
- POC static edges: `orchestrator → intake → analysis`, `remediation → END`.

**Conditional Routing**
- **`need_remediation`** — evaluated after RCA.
  - POC: reads `state["incident_data"]["severity"]`; `"High"` →
    `"approval"`, else `"end"`.
  - Real design: routes to Remediation when the RCA says a change is
    required, otherwise to `END`.
- **`approval_router`** — evaluated inside Remediation.
  - `state["approval"] == "yes"` → `"remediation"` (execute), else
    `"end"`.

**Checkpointer**
- `memory = MemorySaver()` and
  `graph = builder.compile(checkpointer=memory)`.
- Purpose: durable state across HITL pause and any interruption; supports
  resumability from the last checkpoint.
- **Production note:** `MemorySaver` is in-process; for production swap for a
  persistent checkpointer (e.g., SQLite/Redis/Postgres) — *not* done in the
  POC.

**Human-in-the-Loop**
- Implemented inside the Remediation Agent (`approval_agent` in the POC).
- POC uses `input("Approve remediation? (yes/no): ")`.
- Real design: a UI / Slack / Teams approval that shows the RCA and
  recommended steps to the human before they answer.

**Retries / failure handling**
- Not implemented in the POC — routes lead to the next node or `END`.
- Design intent: because state is checkpointed per node, a failing tool call
  can be retried by re-running the node without losing earlier findings.

---

## 9. Tools / MCP

| Tool | Purpose | Input | Output |
| :--- | :--- | :--- | :--- |
| **Excel reader** (POC) / **ServiceNow** (prod) | Fetches the incident record so the Triage Agent can normalize details into shared state. | `incident_id` | `incident_data` (short description, severity, incident type, affected asset) |
| **Ping** | Verifies basic network reachability of the affected asset during initial diagnostics. | Target host / IP | Reachability result |
| **SSH connectivity check** | Confirms the server can be reached and a session established for further diagnostics. | Host + credentials / session | Session status |
| **Switch / router status check** | Verifies the operational state of the network device involved in the incident. | Device identifier | Device status |
| **Log extractor** | Collects relevant logs from the affected asset for correlation and RCA. | Asset + time range | Log snippets |
| **Monitoring / historical health lookup** | Provides past and current health signals of the affected asset for the Diagnostic Agent. | Asset id | Health analysis |
| **RAG store** (Runbooks / SOPs / KB / SharePoint) | Retrieves grounded troubleshooting and resolution steps for the RCA / Analysis Agent. | Incident + health context | Grounded RCA + recommended steps |
| **HITL prompt** | Captures the human's go / no-go decision before any change action is executed. | Prompt (with full context) | `"yes"` / `"no"` |
| **Change / execution tool** | Executes the approved remediation steps against the target system. | Recommended steps | Execution result |
| **`MemorySaver`** (LangGraph checkpointer) | Persists workflow state after every node so the graph is resumable and auditable. | State snapshot | Persisted checkpoint |

**MCP status**
- The POC labels `fetch_incident_from_servicenow(incident_id)` as an "MCP
  TOOL" in a comment, but it is a **plain Python stub** — no MCP server is
  running, no MCP client is used.
- **Design intent:** ServiceNow (and diagnostic tools like ping/SSH/router
  status and the log extractor) would be exposed as **MCP tools** so agents
  can call them through a standard interface.
- **MCP Resources / Prompts:** not implemented in the POC.

---

## 10. Business Value

- **Reduced manual effort** — engineers no longer manually pull incidents,
  run diagnostic commands, chase runbooks, or copy-paste RCA steps.
- **Faster processing / lower MTTR** — Triage → Cmd/Log → Diagnostic → RCA
  runs automatically with shared state; the human's only job is the approval
  decision.
- **Better accuracy** — RCA is grounded via RAG in approved Runbooks / SOPs /
  KB / SharePoint instead of freeform LLM output or tribal knowledge.
- **Operational efficiency** — same 5-agent path for every incident, so
  handling scales with volume, not with headcount.
- **Standardization** — one canonical flow across all on-call engineers.
- **Governance & auditability** — every step (incident, diagnostics, logs,
  health, RCA, approval, remediation) is captured in `IncidentState` and
  checkpointed by `MemorySaver`, giving a complete audit trail.
- **Safety** — investigation agents are read-only; only the Remediation Agent
  can change anything, and only after both the need-remediation gate and the
  HITL approval gate pass.

---

## 11. Interview Explanation

### A) 30-second version
> I built a five-agent LangGraph workflow for production incidents: a Triage
> Agent pulls the ticket (Excel in POC, ServiceNow in prod); a Command
> Executor & Log Extractor Agent runs ping/SSH/router checks and collects
> logs; a Diagnostic Agent analyzes historical and current health; an RCA /
> Analysis Agent uses RAG over runbooks/SOPs/KB/SharePoint; and a Remediation
> Agent executes only after a Human-in-the-Loop approval. State is a typed
> `IncidentState` shared across agents; `MemorySaver` gives resumability.

### B) 1-minute version
> The workflow starts with a **Triage Agent** that fetches incident details —
> Excel in POC, ServiceNow in prod. A **Command Executor & Log Extractor
> Agent** runs initial diagnostic checks per incident type — for network
> incidents that's ping, SSH connectivity, and switch/router status — and
> collects logs. A **Diagnostic Agent** looks at historical and current
> health of the affected VM/server/network device. An **RCA / Analysis
> Agent** does RAG over runbooks / SOPs / KB / SharePoint so the RCA and
> recommended steps are grounded in approved procedures. A conditional edge
> `need_remediation` decides whether remediation is needed; if yes, the
> **Remediation Agent** asks a human for approval. Only on `"yes"` does it
> execute the recommended steps; otherwise the workflow ends. Everything
> runs on a LangGraph `StateGraph` with `MemorySaver`, so state is durable
> and the graph is resumable — important because it pauses at HITL.

### C) 2-minute version
> The problem is that production incidents are handled manually today.
> Engineers pull the ticket from ServiceNow, run diagnostic commands, look at
> monitoring, search runbooks or SharePoint for the fix, chase approvals,
> and execute remediation by hand. It's slow, inconsistent, and unauditable.
>
> I built an Agentic AI workflow in LangGraph with five agents.
>
> **Triage Agent** fetches incident details — Excel in the POC, ServiceNow
> (as an MCP tool) in production — and writes them into a typed
> `IncidentState`.
>
> **Command Executor & Log Extractor Agent** runs initial diagnostics based
> on incident type. For a network incident, that's ping, SSH connectivity,
> switch/router status. It also collects logs and command output.
>
> **Diagnostic Agent** analyzes historical and current health of the affected
> asset using past operational data.
>
> **RCA / Analysis Agent** is the RAG step — it retrieves troubleshooting
> steps from runbooks, SOPs, knowledge base, and SharePoint. This grounds
> RCA in approved procedures rather than freeform LLM output.
>
> **Remediation Agent** is the only agent that changes anything. It has a
> Human-in-the-Loop approval — if the human says `"yes"`, the recommended
> steps execute; if not, the workflow stops.
>
> Two conditional edges enforce safety: a **`need_remediation`** gate after
> RCA, and an **`approval_router`** gate inside Remediation. Investigation
> agents are read-only; only Remediation can act. The graph is compiled
> with `MemorySaver`, so state is checkpointed and the flow can resume —
> important because it pauses at HITL.
>
> The result: end-to-end automation, RAG-grounded RCA, HITL safety, and a
> full audit trail in state. To be transparent: the POC is a LangGraph
> scaffold — the LLM, RAG, real MCP server, and diagnostic tool wiring are
> the next production steps.

---

## 12. Interview Questions (15)

### 1. Explain the architecture end-to-end.
- **Short:** Triage → Cmd/Log → Diagnostic → RCA (RAG) → need-remediation
  gate → Remediation (HITL) → approval gate → Execute. Shared
  `IncidentState`, `MemorySaver` checkpointer.
- **Detailed:** LangGraph `StateGraph(IncidentState)`. The Triage Agent
  reads Excel/ServiceNow; Cmd/Log runs diagnostic checks per incident type
  and collects logs; Diagnostic pulls historical + current health; RCA /
  Analysis uses RAG over runbooks/SOPs/KB/SharePoint to produce grounded
  RCA + recommended steps; a `need_remediation` conditional edge either
  ends the flow or routes to the Remediation Agent; inside Remediation a
  HITL approval gate (`approval_router`) either executes or ends.
  `MemorySaver` checkpoints state after each node for resumability and
  audit.

### 2. Why LangGraph and not LangChain or a plain script?
- **Short:** Because I need typed shared state, conditional routing, HITL
  pause/resume, and checkpointing — LangGraph gives all of that natively.
- **Detailed:** LangChain chains are linear and stateless in the sense the
  project needs. A plain script would hand-roll `if/else`, state passing,
  HITL blocking, and persistence. LangGraph's `StateGraph`,
  `add_conditional_edges`, and `MemorySaver` express exactly what the
  workflow needs, are inspectable, and let each agent stay small and
  testable.

### 3. Why five agents instead of one?
- **Short:** Single responsibility — each agent has one narrow job with its
  own prompt, tools, and errors.
- **Detailed:** Triage is intake, Cmd/Log is diagnostics, Diagnostic is
  health analysis, RCA is retrieval + reasoning, Remediation is HITL +
  execute. Small agents = simpler prompts, easier tool wiring, easier
  observability, and safer separation between investigation (read-only)
  and change actions.

### 4. How does state flow between agents?
- **Short:** A shared `IncidentState` `TypedDict`; each node returns a
  partial dict that LangGraph merges.
- **Detailed:** Triage writes `incident_data`; Cmd/Log writes
  `diagnostic_output` + `logs`; Diagnostic writes `health_analysis`; RCA
  writes `rca` + `recommended_steps`; Remediation writes `approval` and
  `remediation`. Every downstream agent reads the full accumulated state,
  so the HITL step sees complete context.

### 5. How does conditional routing work here?
- **Short:** Two conditional edges — `need_remediation` after RCA and
  `approval_router` after HITL.
- **Detailed:** `need_remediation` inspects state (in the POC,
  `incident_data["severity"]`) and returns `"approval"` or `"end"`.
  `approval_router` inspects `state["approval"]` and returns
  `"remediation"` or `"end"`. Both are wired via
  `add_conditional_edges(node, router_fn, {label: target, ...})`.

### 6. Where is RAG used and how would you implement it?
- **Short:** In the RCA / Analysis Agent, over Runbooks/SOPs/KB/SharePoint.
  The POC does not implement it.
- **Detailed:** Ingest per-source loaders → section-aware chunking →
  embeddings → vector store (PGVector/FAISS/Pinecone/OpenSearch) →
  hybrid retrieval (BM25 + dense) filtered by asset/incident type →
  cross-encoder rerank → LLM composes RCA + recommended_steps grounded in
  the top runbook chunks.

### 7. What tools does the Command Executor & Log Extractor Agent use?
- **Short:** ping, SSH connectivity check, switch/router status check, log
  extractor.
- **Detailed:** Tools are chosen based on incident type. Network-type
  incidents run reachability (ping), device status, and SSH validation;
  server-type incidents run SSH + local log extraction. Outputs are written
  as `diagnostic_output` and `logs` in state.

### 8. Where is Human-in-the-Loop and why is it there?
- **Short:** Inside the Remediation Agent, right before executing any
  change.
- **Detailed:** HITL sits inside Remediation because that's the only place
  a change can happen. The human sees the full state (incident, logs,
  health, RCA, recommended steps) before deciding. `"yes"` → execute,
  anything else → `END`. This keeps all read-only investigation agents
  fully automated and puts the safety gate exactly where risk exists.

### 9. What is MCP in this project?
- **Short:** ServiceNow (and the diagnostic tools) are exposed as MCP
  tools; the POC uses a stub function labeled as an MCP tool.
- **Detailed:** In production, ServiceNow fetch, ping, SSH checks, router
  status and log extractor would all be MCP-exposed tools so agents call
  them through a standard tool interface. The POC (`Langraph.py`) has a
  Python stub `fetch_incident_from_servicenow` labeled "MCP TOOL" — no MCP
  server is actually running.

### 10. How does `MemorySaver` work and why is it used?
- **Short:** In-memory checkpointer attached at compile time
  (`builder.compile(checkpointer=memory)`). Gives resumability + audit.
- **Detailed:** After every node executes, LangGraph persists the merged
  state as a checkpoint. If the graph pauses at HITL or a tool fails, the
  workflow can resume from the last checkpoint. For production, swap
  `MemorySaver` for a persistent store (SQLite/Redis/Postgres) — the POC
  keeps checkpoints in memory only.

### 11. What happens on failures (SSH fails, RAG empty, execution error)?
- **Short:** Not implemented in the POC. Design intent: retry the node
  from the last checkpoint or route to `END`.
- **Detailed:** Because state is checkpointed per node and each node
  returns a partial update, a failing tool call can be retried without
  re-running earlier agents. RAG-empty should surface to the human at
  HITL rather than silently proceed. There is no automatic remediation
  retry loop in this project.

### 12. How is unsafe / hallucinated remediation prevented?
- **Short:** Read-only investigation agents + two conditional gates +
  RAG-grounded steps.
- **Detailed:** Triage, Cmd/Log, Diagnostic and RCA cannot modify the
  target system. The `need_remediation` gate ends the flow when no change
  is needed. The HITL gate blocks execution until a human approves. And
  because RCA's recommended steps come from RAG over approved runbooks,
  the LLM is not inventing procedures.

### 13. What structured outputs are used?
- **Short:** The `IncidentState` `TypedDict` — each field is the typed
  output of one agent.
- **Detailed:** POC fields: `incident_id: str`, `incident_data: dict`,
  `analysis: str`, `approval: str`, `remediation: str`. Real design adds
  `diagnostic_output`, `logs`, `health_analysis`, `rca`,
  `recommended_steps`. These typed slots keep the contract between agents
  predictable.

### 14. What are the security considerations?
- **Short:** Secrets, tool authorization, approver identity, PII in logs,
  and audit.
- **Detailed:** ServiceNow and SSH credentials must be pulled from a
  vault; only the Remediation Agent needs privileges to execute changes
  (least privilege). HITL approver identity must be authenticated and
  logged. Extracted logs may contain PII and need redaction before
  hitting the LLM. `MemorySaver` should be replaced with a persistent
  store for audit retention.

### 15. How would you deploy this?
- **Short:** Containerize the LangGraph app, expose a service endpoint,
  add a persistent checkpointer, integrate the real MCP servers, and put
  the HITL step behind a UI / Slack / Teams approval.
- **Detailed:** Package the graph as a service (FastAPI or worker), swap
  `MemorySaver` for a persistent checkpointer, deploy MCP servers for
  ServiceNow and diagnostic tools, wire the LLM provider with secrets
  management, replace console `input()` with a real approval channel,
  and add logging + tracing (e.g., LangSmith) plus metrics for MTTR and
  approval turnaround.

---

## 13. Follow-up Questions (Top 20)

1. Walk me through the state object and how each agent updates it.
2. Show me the exact `add_conditional_edges` calls and what each returns.
3. Where does the LLM sit today, and which prompts do you plan to use?
4. Why did you pick `MemorySaver` — and what would you use in production?
5. How is the RCA / Analysis Agent's RAG query built from state?
6. How do you keep the runbook index fresh when SOPs change?
7. How would you evaluate the RCA quality end-to-end?
8. How would you handle multi-incident, multi-tenant execution?
9. What happens if two agents try to update the same state field?
10. How does the workflow behave when the human never responds?
11. How do you differentiate incident types to choose diagnostic checks?
12. How do you version the graph when you add or remove agents?
13. What tracing / observability would you add (LangSmith, OpenTelemetry)?
14. What are the failure modes of the HITL step and how do you mitigate them?
15. How do you secure and audit the change execution tool?
16. How does this compare to a Supervisor pattern (like the Patch project)?
17. What would you change to auto-approve low-risk incidents safely?
18. How would you migrate from Excel intake to ServiceNow without breaking
    the graph?
19. What are the cost implications of RAG + LLM calls per incident, and how
    would you optimize?
20. If asked to add a validation/verification step after remediation, where
    would you add it in the graph?
