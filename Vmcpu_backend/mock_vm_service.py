"""
Mock VM Service
Simulates a real Linux VM that the LangGraph agents connect to for health
checks and remediation. Runs on port 3001 (like the switch mock example).

Endpoints:
  POST /api/vm/ping                          -> reachability check
  POST /api/vm/ssh-check                     -> SSH port 22 check
  GET  /api/vm/disk                          -> df -h /
  GET  /api/vm/memory                        -> free -m
  GET  /api/vm/cpu                           -> top -bn1 CPU load
  GET  /api/vm/service/<name>/status         -> systemctl status <name>
  POST /api/vm/service/<name>/restart        -> systemctl restart <name>
  GET  /api/vm/state                         -> full VM state snapshot
  GET  /api/vm/logs                          -> session log
  GET  /health                               -> service health
"""

import os
import time
import random
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("MOCK_VM_PORT", 3001))

# ─────────────────────────────────────────────
# In-memory VM state
# ─────────────────────────────────────────────
vm_state = {
    "vm_ip":         "192.168.1.100",
    "hostname":      "vm-002.prod.local",
    "reachable":     True,
    "ssh_port_open": True,
    "disk": {
        "mount":        "/",
        "total_gb":     100,
        "used_percent": 45,
        # Per-filesystem details reported by `df` on the VM
        "filesystems": [
            {"filesystem": "devtmpfs",  "mount": "/dev",           "size_gb": 16,  "used_percent": 0,  "total_blocks": 16515072, "available_blocks": 16515072},
            {"filesystem": "tmpfs",     "mount": "/dev/shm",       "size_gb": 16,  "used_percent": 1,  "total_blocks": 16515072, "available_blocks": 16349921},
            {"filesystem": "tmpfs",     "mount": "/run",           "size_gb": 4,   "used_percent": 1,  "total_blocks": 4128768,  "available_blocks": 4087480},
            {"filesystem": "/dev/sda1", "mount": "/",              "size_gb": 100, "used_percent": 41, "total_blocks": 261065728,"available_blocks": 154028780},
            {"filesystem": "/dev/sda2", "mount": "/boot",          "size_gb": 1,   "used_percent": 73, "total_blocks": 999320,   "available_blocks": 269816},
            {"filesystem": "/dev/sda3", "mount": "/boot/efi",      "size_gb": 1,   "used_percent": 3,  "total_blocks": 523248,   "available_blocks": 507564},
            {"filesystem": "/dev/sdb1", "mount": "/opt/new_genai", "size_gb": 200, "used_percent": 1,  "total_blocks": 524288000,"available_blocks": 519045120},
        ],
    },
    "memory": {
        "total_mb":          8192,
        "used_percent":      62,
        "used_mb":           5079,
        "free_mb":           3113,
        "available_mb":      4096,
        "free_percent":      38,
        "available_percent": 50,
    },
    "cpu": {
        "cores":        4,
        "load_percent": 38.5,
    },
    # apache2 is stopped to match the ServiceNow incident INC0887758
    "services": {
        "apache2": {"state": "stopped", "pid": 0,    "uptime_sec": 0},
        "nginx":   {"state": "running", "pid": 2451, "uptime_sec": 86400},
        "mysql":   {"state": "running", "pid": 1892, "uptime_sec": 172800},
    },
    "session_log": [],
}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def log(message: str):
    ts = datetime.utcnow().isoformat()
    vm_state["session_log"].append({"timestamp": ts, "message": message})
    print(f"[{ts}] {message}")


def simulate_delay(min_ms=100, max_ms=400):
    time.sleep(random.uniform(min_ms, max_ms) / 1000.0)


# ─────────────────────────────────────────────
# Root – index of all endpoints (so / doesn't 404)
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "mock-vm",
        "hostname": vm_state["hostname"],
        "vm_ip": vm_state["vm_ip"],
        "message": "Mock VM service is running. Use the endpoints below to view JSON output.",
        "endpoints": {
            "health":            "GET  /health",
            "full_state":        "GET  /api/vm/state",
            "session_log":       "GET  /api/vm/logs",
            "ping":              "POST /api/vm/ping",
            "ssh_check":         "POST /api/vm/ssh-check",
            "disk":              "GET  /api/vm/disk",
            "memory":            "GET  /api/vm/memory",
            "cpu":               "GET  /api/vm/cpu",
            "service_status":    "GET  /api/vm/service/<name>/status   (e.g. apache2)",
            "service_restart":   "POST /api/vm/service/<name>/restart  (e.g. apache2)",
            "reset_demo_state":  "POST /api/vm/reset",
        }
    })


# ─────────────────────────────────────────────
# Reachability
# ─────────────────────────────────────────────
@app.route("/api/vm/ping", methods=["POST"])
def ping():
    simulate_delay()
    log(f"Ping request to {vm_state['vm_ip']}")
    if not vm_state["reachable"]:
        return jsonify({
            "success":  False,
            "vm_ip":    vm_state["vm_ip"],
            "output":   f"Request timed out for {vm_state['vm_ip']}",
        }), 200
    rtt_ms = round(random.uniform(0.4, 2.1), 2)
    return jsonify({
        "success":  True,
        "vm_ip":    vm_state["vm_ip"],
        "hostname": vm_state["hostname"],
        "rtt_ms":   rtt_ms,
        "output":   f"Reply from {vm_state['vm_ip']}: bytes=32 time={rtt_ms}ms TTL=64",
    })


@app.route("/api/vm/ssh-check", methods=["POST"])
def ssh_check():
    simulate_delay()
    log(f"SSH port check on {vm_state['vm_ip']}:22")
    open_ = vm_state["reachable"] and vm_state["ssh_port_open"]
    return jsonify({
        "success":  open_,
        "vm_ip":    vm_state["vm_ip"],
        "hostname": vm_state["hostname"],
        "port":     22,
        "state":    "open" if open_ else "closed",
        "output":   "Connection to 192.168.1.100 22 port [tcp/ssh] succeeded!" if open_ else "ssh: connect to host 192.168.1.100 port 22: Connection refused",
    })


# ─────────────────────────────────────────────
# Disk / Memory / CPU
# ─────────────────────────────────────────────
@app.route("/api/vm/disk", methods=["GET"])
def disk():
    simulate_delay()
    log("Disk usage requested (df -h)")
    vm_state["disk"]["used_percent"] = max(30, min(85, vm_state["disk"]["used_percent"] + random.randint(-2, 2)))
    used = vm_state["disk"]["used_percent"]
    total = vm_state["disk"]["total_gb"]
    used_gb = round(total * used / 100, 1)
    avail_gb = round(total - used_gb, 1)

    # Keep root FS in sync with the drifting used_percent
    filesystems = list(vm_state["disk"]["filesystems"])
    for fs in filesystems:
        if fs["mount"] == "/":
            fs["used_percent"] = used

    df_lines = ["Filesystem      Size  Used Avail Use% Mounted on"]
    for fs in filesystems:
        df_lines.append(
            f"{fs['filesystem']:<15} {fs['size_gb']}G  {fs['used_percent']}%  {fs['mount']}"
        )

    return jsonify({
        "mount":         vm_state["disk"]["mount"],
        "total_gb":      total,
        "used_gb":       used_gb,
        "available_gb":  avail_gb,
        "used_percent":  used,
        "healthy":       used < 90,
        "filesystems":   filesystems,
        "output":        "\n".join(df_lines),
    })


@app.route("/api/vm/memory", methods=["GET"])
def memory():
    simulate_delay()
    log("Memory usage requested (free -m)")
    vm_state["memory"]["used_percent"] = max(35, min(88, vm_state["memory"]["used_percent"] + random.randint(-3, 3)))
    used = vm_state["memory"]["used_percent"]
    total = vm_state["memory"]["total_mb"]
    used_mb = int(total * used / 100)
    free_mb = total - used_mb
    available_mb = free_mb + 512
    free_pct = round(free_mb * 100 / total, 1)
    available_pct = round(available_mb * 100 / total, 1)
    return jsonify({
        "total_mb":              total,
        "used_mb":               used_mb,
        "free_mb":               free_mb,
        "available_mb":          available_mb,
        "used_percent":          used,
        "free_percent":          free_pct,
        "available_percent":     available_pct,
        "healthy":               used < 90,
        "output": (
            "              total        used        free      shared  buff/cache   available\n"
            f"Mem:          {total}       {used_mb}        {free_mb}         120        1024        {available_mb}\n"
            "Swap:         2048           0        2048"
        ),
    })


@app.route("/api/vm/cpu", methods=["GET"])
def cpu():
    simulate_delay()
    log("CPU load requested (top -bn1)")
    vm_state["cpu"]["load_percent"] = round(max(10.0, min(90.0, vm_state["cpu"]["load_percent"] + random.uniform(-4, 4))), 1)
    load = vm_state["cpu"]["load_percent"]
    return jsonify({
        "cores":         vm_state["cpu"]["cores"],
        "load_percent":  load,
        "healthy":       load < 85,
        "output": (
            f"top - {datetime.utcnow().strftime('%H:%M:%S')} up 12 days,  3:14,  1 user,  load average: {load/25:.2f}, {load/28:.2f}, {load/30:.2f}\n"
            "Tasks: 214 total,   1 running, 213 sleeping,   0 stopped,   0 zombie\n"
            f"%Cpu(s): {load:.1f} us,  1.2 sy,  0.0 ni, {100-load-1.2:.1f} id"
        ),
    })


# ─────────────────────────────────────────────
# Services (systemctl)
# ─────────────────────────────────────────────
@app.route("/api/vm/service/<name>/status", methods=["GET"])
def service_status(name):
    simulate_delay()
    log(f"systemctl status {name}")
    svc = vm_state["services"].get(name)
    if svc is None:
        return jsonify({
            "success": False,
            "service": name,
            "error":   "unit not found",
            "output":  f"Unit {name}.service could not be found.",
        }), 404

    active = "active (running)" if svc["state"] == "running" else \
             "inactive (dead)"  if svc["state"] == "stopped" else \
             "activating (auto-restart)"

    is_running = svc["state"] == "running"
    status_message = {
        "running":  f"{name} is running normally",
        "stopped":  f"{name} is not running",
        "abnormal": f"{name} is in an abnormal state",
    }.get(svc["state"], f"{name} state: {svc['state']}")

    systemctl_output = (
        f"● {name}.service - {name.title()} Web Server\n"
        f"   Loaded: loaded (/lib/systemd/system/{name}.service; enabled)\n"
        f"   Active: {active}\n"
        f"   Main PID: {svc['pid']}\n"
        f"   CGroup: /system.slice/{name}.service"
    )

    return jsonify({
        "success":          True,
        "service":          name,
        "state":            svc["state"],
        "pid":              svc["pid"],
        "uptime_sec":       svc["uptime_sec"],
        "healthy":          is_running,
        "service_status":   is_running,
        "active_state":     active,
        "status_message":   status_message,
        "systemctl_output": systemctl_output,
        "output":           systemctl_output,
    })


@app.route("/api/vm/service/<name>/restart", methods=["POST"])
def service_restart(name):
    simulate_delay(500, 1200)
    log(f"systemctl restart {name}")
    svc = vm_state["services"].get(name)
    if svc is None:
        return jsonify({
            "success": False,
            "service": name,
            "error":   "unit not found",
        }), 404

    prev_state = svc["state"]
    # Simulate restart -> service becomes running with a fresh PID
    svc["state"]      = "running"
    svc["pid"]        = random.randint(1000, 9999)
    svc["uptime_sec"] = 0

    log(f"Service '{name}' restarted (was {prev_state}, now running, pid={svc['pid']})")
    return jsonify({
        "success":    True,
        "service":    name,
        "prev_state": prev_state,
        "state":      "running",
        "pid":        svc["pid"],
        "output": (
            f"Restarting {name}.service...\n"
            f"● {name}.service - {name.title()} Web Server\n"
            f"   Active: active (running) since {datetime.utcnow().isoformat()}\n"
            f"   Main PID: {svc['pid']}"
        ),
    })


# ─────────────────────────────────────────────
# State / Logs / Health
# ─────────────────────────────────────────────
@app.route("/api/vm/state", methods=["GET"])
def state_dump():
    return jsonify(vm_state)


@app.route("/api/vm/logs", methods=["GET"])
def logs():
    return jsonify({"logs": vm_state["session_log"]})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "healthy",
        "service":   "mock-vm",
        "vm_ip":     vm_state["vm_ip"],
        "timestamp": datetime.utcnow().isoformat(),
    })


# ─────────────────────────────────────────────
# Demo helper: reset state (so you can re-run the workflow cleanly)
# ─────────────────────────────────────────────
@app.route("/api/vm/reset", methods=["POST"])
def reset():
    vm_state["services"]["apache2"] = {"state": "stopped", "pid": 0, "uptime_sec": 0}
    vm_state["disk"]["used_percent"]   = 45
    vm_state["memory"]["used_percent"] = 62
    vm_state["cpu"]["load_percent"]    = 38.5
    vm_state["session_log"].clear()
    log("VM state reset (apache2 back to stopped)")
    return jsonify({"success": True, "message": "VM state reset"})


@app.errorhandler(500)
def internal_error(e):
    print(str(e))
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    print(f"[MOCK-VM] Mock VM Service running on port {PORT}")
    print(f"[MOCK-VM] Simulated VM: {vm_state['hostname']} ({vm_state['vm_ip']})")
    print(f"[MOCK-VM] Endpoints:    http://localhost:{PORT}/api/vm/*")
    print(f"[MOCK-VM] Health:       http://localhost:{PORT}/health")
    log("Mock VM service started")
    app.run(host="0.0.0.0", port=PORT)
