"""
Backend API Server for VM Stabilizer
Provides:
  - GET /api/servicenow/incidents  → fetch tickets from ServiceNow
  - GET /api/agents/event-stream   → stream agent task events (SSE)
  - POST /api/agents/event         → agents log events
"""

from flask import Flask, jsonify, Response, request, send_file
from flask_cors import CORS
import json
import time
import queue
from datetime import datetime
import uuid
import threading
import os

app = Flask(__name__)
CORS(app)

# In-memory event store
event_queue = []
event_lock = threading.Lock()

# Live streaming state for /run_vm_stabilizer_stream_live
live_output_queue = None
all_agent_outputs = []

# Pending human-approval decisions: thread_id -> queue.Queue()
# When a workflow hits the human-in-the-loop interrupt it registers a queue
# here and blocks on it. The /submit_decision endpoint drops the user's
# decision into that queue, unblocking the workflow.
pending_decisions = {}
pending_decisions_lock = threading.Lock()

# How long the workflow waits for the operator to click approve/reject
DECISION_TIMEOUT_SECONDS = 600

# ─────────────────────────────────────────────
# Root Endpoint (Serve Frontend)
# ─────────────────────────────────────────────
@app.route('/', methods=['GET'])
def root():
    """Serve the frontend HTML"""
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), 'frontend.html')
        if os.path.exists(frontend_path):
            return send_file(frontend_path, mimetype='text/html')
        else:
            return jsonify({"message": "VM Stabilizer Backend API", "version": "1.0"}), 200
    except Exception as e:
        return jsonify({"message": "VM Stabilizer Backend API", "version": "1.0"}), 200

# ─────────────────────────────────────────────
# ServiceNow Incidents Endpoint
# ─────────────────────────────────────────────
@app.route('/api/servicenow/incidents', methods=['GET'])
def get_incidents():
    """Fetch incidents from ServiceNow"""
    incidents = {
        "identified_tickets": 1,
        "tickets_info": [
            {
                "description": "VM Service Breach",
                "incident_number": "INC0887758",
                "short_description": "apache2 service stopped on VM-002",
                "main_description": "VM-002 has apache2 service stopped, affecting users. Requires immediate restart.",
                "priority": "1 - High",
                "created_on": "2026-07-29T08:14:22Z",
                "interface": None,
                "port_type": None,
                "switch": None,
                "url": "https://servicenow.com/api/now/table/incident/fe8da6d42b9c7e90",
                "vlan": None,
                "service_name": "apache2",
                "vm_ip": "192.168.1.100",
                "state": "stopped",
                "affected_ci": {
                    "name": "vm-002.prod.local",
                    "ip_address": "192.168.1.100",
                    "environment": "Production",
                    "operating_system": "Ubuntu 22.04 LTS",
                    "service_offering": "Web Hosting Platform",
                    "application_id": "APP-0421",
                    "host": "vm-002.prod.local",
                    "datacenter": "US-EAST-1 / Rack B12"
                }
            }
        ]
    }
    return jsonify(incidents)


# ─────────────────────────────────────────────
# Add Event (agents call this)
# ─────────────────────────────────────────────
@app.route('/api/agents/event', methods=['POST'])
def add_event():
    """Agents POST events to log their work"""
    data = request.get_json()
    
    with event_lock:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "agent": data.get("agent", "Unknown"),
            "task": data.get("task", ""),
            "description": data.get("description", ""),
            "output": data.get("output", ""),
            "formatted_output": data.get("formatted_output", ""),
            "status": data.get("status", "running")
        }

        event_queue.append(event)
    
    return jsonify({"status": "success", "event_id": event["id"]})


# ─────────────────────────────────────────────
# Event Stream (Server-Sent Events)
# ─────────────────────────────────────────────
@app.route('/api/agents/event-stream', methods=['GET'])
def event_stream():
    """Stream events via Server-Sent Events"""
    def generate():
        last_index = 0
        while True:
            with event_lock:
                if last_index < len(event_queue):
                    for event in event_queue[last_index:]:
                        yield f"data: {json.dumps(event)}\n\n"
                    last_index = len(event_queue)
            
            time.sleep(0.3)
    
    return Response(generate(), mimetype="text/event-stream")


# ─────────────────────────────────────────────
# Get All Events
# ─────────────────────────────────────────────
@app.route('/api/agents/events', methods=['GET'])
def get_events():
    """Get all events"""
    with event_lock:
        return jsonify({"events": event_queue})


# ─────────────────────────────────────────────
# Clear Events
# ─────────────────────────────────────────────
@app.route('/api/agents/events/clear', methods=['POST'])
def clear_events():
    """Clear all events"""
    global event_queue
    with event_lock:
        event_queue = []
    return jsonify({"status": "success", "message": "Events cleared"})


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})


# ─────────────────────────────────────────────
# Trigger Workflow + Stream Agent Outputs Live (SSE)
# ─────────────────────────────────────────────
@app.route('/run_vm_stabilizer_stream_live', methods=['POST', 'OPTIONS'])
def run_vm_stabilizer_stream_live():
    """
    Trigger the LangGraph VM Stabilizer workflow and stream each agent's
    output live via Server-Sent Events on the same connection.

    Flow:
        1. Client POSTs to this endpoint -> workflow starts, agents stream.
        2. Workflow hits the human-in-the-loop interrupt.
        3. Server pushes an 'awaiting_approval' SSE event containing a
           thread_id.
        4. Client POSTs {"thread_id": ..., "decision": "approve"|"reject"}
           to /submit_decision.
        5. Workflow resumes:
              - approve -> RestartProcessAgent -> END
              - reject  -> SkipAgent            -> END
        6. Remaining agent events stream, then a 'completed' event closes.

    Request body (JSON):
        { "request": { ... optional workflow input overrides ... } }
    """
    global live_output_queue, all_agent_outputs

    if request.method == 'OPTIONS':
        return Response('', status=204, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Cache-Control',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        })

    try:
        data = request.get_json(force=True, silent=True) or {}
        workflow_input = data.get("request", {}) or {}
        print(f"[stream_live] Triggering workflow. input={workflow_input}")

        def generate():
            global live_output_queue, all_agent_outputs
            live_output_queue = queue.Queue()
            all_agent_outputs = []

            # Import here to avoid circular import at module load
            from vm_cpu_stabilizer import build_graph, set_live_queue
            from langgraph.types import Command

            thread_id = f"vm-stabilizer-{uuid.uuid4()}"

            def execute_workflow():
                decision_queue = queue.Queue()
                with pending_decisions_lock:
                    pending_decisions[thread_id] = decision_queue

                try:
                    # Register the live queue so log_event() streams to us
                    set_live_queue(live_output_queue)

                    graph = build_graph()

                    initial_state = {
                        "vm_ip":                workflow_input.get("vm_ip", ""),
                        "snow_incident_id":     "",
                        "snow_service":         "",
                        "snow_state":           "",
                        "plan":                 [],
                        "plan_structured":      {},
                        "reachable":            False,
                        "disk_healthy":         False,
                        "memory_ok":            False,
                        "cpu_ok":               False,
                        "process_state":        "",
                        "process_pid":          0,
                        "ci_details":           {},
                        "connectivity_findings":{},
                        "disk_findings":        {},
                        "memory_findings":      {},
                        "cpu_findings":         {},
                        "process_findings":     {},
                        "diagnosis":            {},
                        "human_approved":       False,
                        "report":               []
                    }

                    config = {"configurable": {"thread_id": thread_id}}

                    # ── Run graph until it hits the human-approval interrupt ──
                    for _ in graph.stream(initial_state, config=config, stream_mode="values"):
                        pass

                    # ── Tell the client we need a decision ──
                    live_output_queue.put({
                        "type": "awaiting_approval",
                        "content": {
                            "thread_id": thread_id,
                            "message": "Awaiting operator decision (approve/reject).",
                            "options": ["approve", "reject"],
                            "timeout_seconds": DECISION_TIMEOUT_SECONDS
                        }
                    })

                    # ── Block until /submit_decision is called ──
                    try:
                        human_decision = decision_queue.get(timeout=DECISION_TIMEOUT_SECONDS)
                    except queue.Empty:
                        live_output_queue.put({
                            "type": "error",
                            "content": f"Timed out after {DECISION_TIMEOUT_SECONDS}s waiting for approval."
                        })
                        return

                    human_decision = str(human_decision).strip().lower()
                    if human_decision not in ("approve", "reject"):
                        human_decision = "reject"

                    # ── Resume graph with the operator's decision ──
                    # approve -> restart_process -> END
                    # reject  -> skip            -> END
                    for _ in graph.stream(
                        Command(resume=human_decision),
                        config=config,
                        stream_mode="updates"
                    ):
                        pass

                    final_state = graph.get_state(config).values

                    live_output_queue.put({
                        "type": "completion",
                        "content": {
                            "thread_id": thread_id,
                            "decision": human_decision,
                            "report": final_state.get("report", []),
                            "snow_incident_id": final_state.get("snow_incident_id", ""),
                            "snow_service": final_state.get("snow_service", ""),
                            "vm_ip": final_state.get("vm_ip", "")
                        }
                    })
                except Exception as ex:
                    live_output_queue.put({"type": "error", "content": str(ex)})
                finally:
                    set_live_queue(None)
                    with pending_decisions_lock:
                        pending_decisions.pop(thread_id, None)

            workflow_thread = threading.Thread(target=execute_workflow, daemon=True)
            workflow_thread.start()

            # Initial status ping so the client knows the stream is live
            yield f"data: {json.dumps({'status': 'started', 'thread_id': thread_id, 'message': 'Workflow started'})}\n\n"

            completed = False
            sent_agents = set()

            while not completed:
                try:
                    output_item = live_output_queue.get(timeout=5.0)

                    if output_item['type'] == 'live_output':
                        payload = output_item['content']
                        agent_name = payload.get('agent', 'Unknown Agent')

                        # Dedup: only send first event per agent name in a run
                        # (comment out the next 2 lines if you want ALL events)
                        if agent_name in sent_agents:
                            continue
                        sent_agents.add(agent_name)

                        all_agent_outputs.append(payload)

                        live_message = {
                            "agent": agent_name,
                            "task": payload.get('task', ''),
                            "description": payload.get('description', ''),
                            "output": payload.get('output', ''),
                            "formatted_output": payload.get('formatted_output', ''),
                            "status": payload.get('status', 'completed'),
                            "timestamp": payload.get('timestamp', datetime.now().isoformat())
                        }
                        yield f"data: {json.dumps(live_message, ensure_ascii=True)}\n\n"

                    elif output_item['type'] == 'awaiting_approval':
                        approval_message = {
                            "status": "awaiting_approval",
                            **output_item['content']
                        }
                        yield f"data: {json.dumps(approval_message, ensure_ascii=True)}\n\n"

                    elif output_item['type'] == 'completion':
                        summary = output_item['content']
                        final_message = {
                            "status": "completed",
                            "message": "Workflow finished",
                            "summary": summary,
                            "agents_streamed": len(all_agent_outputs)
                        }
                        yield f"data: {json.dumps(final_message, ensure_ascii=True)}\n\n"
                        completed = True

                    elif output_item['type'] == 'error':
                        yield f"data: {json.dumps({'error': output_item['content']})}\n\n"
                        completed = True

                except queue.Empty:
                    # Heartbeat to keep proxies from closing the connection
                    yield f": keep-alive\n\n"
                    if not workflow_thread.is_alive():
                        completed = True

        return Response(generate(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Cache-Control',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'X-Accel-Buffering': 'no',
            'Transfer-Encoding': 'chunked'
        })

    except Exception as e:
        error_message = f"data: {json.dumps({'error': str(e)})}\n\n"
        return Response(
            iter([error_message]),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'X-Accel-Buffering': 'no'
            }
        )


# ─────────────────────────────────────────────
# Submit human-in-the-loop decision (approve / reject)
# ─────────────────────────────────────────────
@app.route('/submit_decision', methods=['POST', 'OPTIONS'])
def submit_decision():
    """
    Deliver the operator's approve/reject decision to a workflow that is
    paused at the human-in-the-loop interrupt.

    Request body (JSON):
        { "thread_id": "vm-stabilizer-...", "decision": "approve" | "reject" }
    """
    if request.method == 'OPTIONS':
        return Response('', status=204, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Cache-Control',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        })

    data = request.get_json(force=True, silent=True) or {}
    thread_id = data.get("thread_id")
    decision = str(data.get("decision", "")).strip().lower()

    if not thread_id:
        return jsonify({"error": "Missing 'thread_id'"}), 400
    if decision not in ("approve", "reject"):
        return jsonify({"error": "'decision' must be 'approve' or 'reject'"}), 400

    with pending_decisions_lock:
        decision_queue = pending_decisions.get(thread_id)

    if decision_queue is None:
        return jsonify({
            "error": f"No workflow awaiting approval with thread_id={thread_id}"
        }), 404

    decision_queue.put(decision)
    return jsonify({
        "status": "ok",
        "thread_id": thread_id,
        "decision": decision
    })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  VM Stabilizer Backend API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET  /                              (serve frontend)")
    print("  GET  /health")
    print("  GET  /api/servicenow/incidents")
    print("  GET  /api/agents/event-stream       (Server-Sent Events)")
    print("  POST /api/agents/event              (add event)")
    print("  GET  /api/agents/events             (get all events)")
    print("  POST /api/agents/events/clear       (clear all events)")
    print("  POST /run_vm_stabilizer_stream_live (trigger workflow + stream)")
    print("  POST /submit_decision               (approve/reject the workflow)")
    print("\nServer running on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
