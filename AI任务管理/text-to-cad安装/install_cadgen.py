# -*- coding: utf-8 -*-
"""L1-2.1/L1-2.2: 安装 cadgen（uvx，官方 pin 0.7.21）并跑 doctor。
本机经验：结果一律写文件；stdin 接 DEVNULL 防交互挂起；首次运行要下载
managed python 3.13 + cadgen + OCP（上百 MB），给足超时。
"""
import os, json, time, subprocess, urllib.request

OUT = r"D:\.AI\GITHUB\trae-dcs-skills\AI任务管理\text-to-cad安装"
LOG = os.path.join(OUT, "安装记录_20261018.txt")
UV = r"C:\Users\nczdl\.local\bin\uv.exe"
UVX = r"C:\Users\nczdl\.local\bin\uvx.exe"
PIN = "0.7.21"   # 仓库 mcp.json 官方 pin（2026-10-18 核实）

lines = []


def log(s=""):
    lines.append(s)
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(cmd, timeout):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired:
        return None, "", f"TIMEOUT after {timeout}s", time.time() - t0
    except Exception as e:
        return None, "", f"EXC {e!r}", time.time() - t0


log("# cadgen 安装记录  2026-10-18")
log(f"# uv={UV} 存在:{os.path.exists(UV)}  uvx={UVX} 存在:{os.path.exists(UVX)}")
log()

log("== [1] uv python list（本地已有 python 快查） ==")
rc, out, err, dt = run([UV, "python", "list"], 60)
log(f"rc={rc} {dt:.1f}s")
log((out or "").strip() or "(no stdout)")
if (err or "").strip():
    log("[stderr] " + err.strip())
log()

log("== [2] PyPI cadgen 最新版（best-effort，失败不阻塞） ==")
try:
    req = urllib.request.Request("https://pypi.org/pypi/cadgen/json",
                                 headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    log(f"PyPI latest = {data['info']['version']}")
except Exception as e:
    log(f"PyPI 查询失败: {e!r}")
log(f"仓库官方 pin = {PIN} -> 采用 {PIN}（与官方 mcp.json 一致）")
log()

base = [UVX, "--no-config", "--managed-python", "--python", "3.13",
        "--from", f"cadgen=={PIN}"]

log("== [3] uvx ... cadgen --help（首次下载 managed py3.13+cadgen+OCP，可能数分钟） ==")
rc, out, err, dt = run(base + ["cadgen", "--help"], 570)
log(f"rc={rc} 耗时={dt:.1f}s")
log("--- stdout ---")
log((out or "").strip() or "(empty)")
log("--- stderr ---")
log((err or "").strip() or "(empty)")
log()

if rc == 0:
    log("== [4] uvx ... cadgen doctor ==")
    rc2, out2, err2, dt2 = run(base + ["cadgen", "doctor"], 300)
    log(f"rc={rc2} 耗时={dt2:.1f}s")
    log("--- stdout ---")
    log((out2 or "").strip() or "(empty)")
    log("--- stderr ---")
    log((err2 or "").strip() or "(empty)")
else:
    log("== [4] 跳过 doctor（--help 未成功） ==")

log()
log("== DONE ==")
print("OK")
