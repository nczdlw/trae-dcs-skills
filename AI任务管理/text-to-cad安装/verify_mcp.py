# -*- coding: utf-8 -*-
"""L1-3.2: 按 mcp.json 中 cadgen 条目原样启动 MCP server 并握手验证
（initialize -> notifications/initialized -> tools/list）。
方法参照知识库 CAD_MCP 安装配置说明第五节。stdout/stderr 均用守护线程读，
避免管道写满死锁；recv 带超时，防止服务器无响应时挂死。
"""
import os, json, queue, subprocess, sys, threading, time

MCP = r"C:\Users\nczdl\.workbuddy\mcp.json"
REPORT = r"D:\.AI\GITHUB\trae-dcs-skills\AI任务管理\text-to-cad安装\mcp握手验证_20261018.txt"

lines = []


def log(s=""):
    lines.append(s)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


with open(MCP, "r", encoding="utf-8") as f:
    cfg = json.load(f)

if "cadgen" not in cfg.get("mcpServers", {}):
    log("!! mcp.json 中无 cadgen 条目，先跑 update_mcp.py")
    print("FAIL")
    sys.exit(1)

srv = cfg["mcpServers"]["cadgen"]
cmd = [srv["command"]] + list(srv.get("args", []))
env = dict(os.environ)
env.update(srv.get("env") or {})

log("# cadgen MCP 握手验证  2026-10-18")
log("启动命令: " + " ".join(cmd))
log("cwd: C:\\")

p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env, cwd="C:\\",
                     text=True, bufsize=1)

q = queue.Queue()
stderr_lines = []


def reader():
    for line in p.stdout:
        q.put(line)


def errreader():
    for line in p.stderr:
        stderr_lines.append(line)


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=errreader, daemon=True).start()


def send(obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def recv(timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            line = q.get(timeout=1)
        except queue.Empty:
            continue
        s = line.strip()
        if not s:
            continue
        try:
            return json.loads(s)
        except Exception:
            log(f"[非JSON行] {s[:200]}")
    return None


r1 = r2 = None
try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "wb-verify", "version": "1.0"}}})
    t0 = time.time()
    r1 = recv(240)
    log(f"initialize -> {'%.1fs' % (time.time() - t0)}: "
        + (json.dumps(r1, ensure_ascii=False)[:800] if r1 else "NO RESPONSE"))
    if r1 and "result" in r1:
        log("serverInfo = " + json.dumps(r1["result"].get("serverInfo"), ensure_ascii=False))
        log("protocolVersion = " + str(r1["result"].get("protocolVersion")))

    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    r2 = recv(120)
    if r2 and "result" in r2:
        tools = r2["result"].get("tools", [])
        log(f"tools/list -> {len(tools)} 个工具")
        for t in tools:
            desc = (t.get("description") or "").replace("\n", " ")
            log(f"  - {t.get('name')}: {desc[:90]}")
    else:
        log("tools/list -> " + (json.dumps(r2, ensure_ascii=False)[:800] if r2 else "NO RESPONSE"))
finally:
    try:
        p.stdin.close()
    except Exception:
        pass
    try:
        p.terminate()
    except Exception:
        pass
    time.sleep(1)
    if stderr_lines:
        log("--- stderr(前2000字) ---")
        log("".join(stderr_lines)[:2000])

ok = bool(r1 and "result" in r1) and bool(r2 and "result" in r2)
log(f"握手结论: {'OK' if ok else 'FAIL'}")
print("OK" if ok else "FAIL")
