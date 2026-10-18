# -*- coding: utf-8 -*-
"""text-to-cad 安装任务 L1-1 环境检查。
本机经验：PowerShell stdout 常丢失、Bash PATH 不稳 → 全部结果写文件，再用 Read 工具读。
覆盖 L1-1.1(uv/uvx) / L1-1.2(Windows+SAC) / L1-1.3(agents+mcp.json)。
"""
import os, json, shutil, subprocess, winreg

OUT = r"D:\.AI\GITHUB\trae-dcs-skills\AI任务管理\text-to-cad安装"
os.makedirs(OUT, exist_ok=True)
STAMP = "2026-10-18"


def w(name, lines):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return p


# ---------- L1-1.1 uv / uvx ----------
lines = [f"# L1-1.1 uv/uvx 检查  {STAMP}", ""]
for label, path in [
    ("uv", r"C:\Users\nczdl\.local\bin\uv.exe"),
    ("uvx", r"C:\Users\nczdl\.local\bin\uvx.exe"),
]:
    lines.append(f"[{label}] 路径: {path}  存在: {os.path.exists(path)}")
    if os.path.exists(path):
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30)
            out = (r.stdout or "").strip() or (r.stderr or "").strip()
            lines.append(f"  --version -> rc={r.returncode}  输出: {out}")
        except Exception as e:
            lines.append(f"  执行异常: {e!r}")
for exe in ("uv", "uvx"):
    lines.append(f"shutil.which({exe!r}) -> {shutil.which(exe)}")
w("环境检查_uv.txt", lines)

# ---------- L1-1.2 Windows 版本 + Smart App Control ----------
lines = [f"# L1-1.2 Windows 版本与 Smart App Control  {STAMP}", ""]
try:
    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")

    def qv(k, n):
        try:
            return winreg.QueryValueEx(k, n)[0]
        except Exception:
            return None

    product = qv(k, "ProductName")
    build = qv(k, "CurrentBuildNumber")
    ubr = qv(k, "UBR")
    display = qv(k, "DisplayVersion")
    lines.append(f"ProductName={product}  DisplayVersion={display}  CurrentBuild={build}  UBR={ubr}")
    try:
        b = int(str(build))
        lines.append(f"Windows 11 判定(build>=22000): {b >= 22000}")
    except Exception as e:
        lines.append(f"build 解析失败: {e!r}")
except Exception as e:
    lines.append(f"读版本注册表键失败: {e!r}")
lines.append("")
sac_key = r"SYSTEM\CurrentControlSet\Control\CI\Policy"
sac_val_name = "VerifiedAndReputationPolicyState"
try:
    k2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sac_key)
    val = winreg.QueryValueEx(k2, sac_val_name)[0]
    meaning = {0: "0=OFF(关闭)", 1: "1=ON(开启)", 2: "2=EVALUATION(评估模式)"}.get(val, f"未知值({val})")
    lines.append(f"SAC {sac_val_name} = {val}  ({meaning})")
except Exception as e:
    lines.append(f"读 SAC 键 {sac_key}\\{sac_val_name} 失败: {e!r}")
    lines.append("  -> 键或值不存在通常意味着 SAC 不可用/未配置（不等于开启）")
w("环境检查_win.txt", lines)

# ---------- L1-1.3 agents + mcp.json ----------
lines = [f"# L1-1.3 已装 agent 盘点 + mcp.json 现状  {STAMP}", ""]
home = os.path.expanduser("~")
lines.append(f"HOME={home}")
npm_g = os.path.join(home, "AppData", "Roaming", "npm")
lines.append(f"npm 全局目录 {npm_g} 存在: {os.path.isdir(npm_g)}")
if os.path.isdir(npm_g):
    try:
        hits = sorted(n for n in os.listdir(npm_g)
                      if n.lower().startswith(("claude", "codex", "gemini", "cursor", "grok")))
        lines.append(f"npm 全局中的相关 CLI: {hits}")
    except Exception as e:
        lines.append(f"列 npm 全局目录失败: {e!r}")
for d in (".claude", ".codex", ".gemini", ".cursor", ".grok"):
    p = os.path.join(home, d)
    lines.append(f"{p} 存在: {os.path.isdir(p)}")
for p in (os.path.join(home, "AppData", "Local", "Programs", "cursor"),
          os.path.join(home, "AppData", "Local", "Programs", "Cursor"),
          os.path.join(home, "AppData", "Local", "Programs", "Microsoft VS Code")):
    lines.append(f"{p} 存在: {os.path.isdir(p)}")
lines.append("")
mcp_path = r"C:\Users\nczdl\.workbuddy\mcp.json"
lines.append(f"mcp.json 路径: {mcp_path}  存在: {os.path.exists(mcp_path)}")
if os.path.exists(mcp_path):
    try:
        with open(mcp_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        servers = cfg.get("mcpServers", {})
        lines.append(f"现有 mcpServers 键({len(servers)}): {sorted(servers.keys())}")
        for k in sorted(servers.keys()):
            v = servers[k] or {}
            lines.append(f"  - {k}: command={v.get('command')!r} args={v.get('args')!r} env_keys={list((v.get('env') or {}).keys())}")
    except Exception as e:
        lines.append(f"读 mcp.json 失败: {e!r}")
w("环境检查_agents.txt", lines)

print("OK")
for n in ("环境检查_uv.txt", "环境检查_win.txt", "环境检查_agents.txt"):
    print(os.path.join(OUT, n))
