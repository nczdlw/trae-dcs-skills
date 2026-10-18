# -*- coding: utf-8 -*-
"""L1-3.1: 在 WorkBuddy mcp.json 中新增 cadgen 条目。
规则：先备份再改；合并写入；原有 cad-mcp/autocad-draft/rea 三条必须逐字保留；
command 用 uvx 绝对路径（本机 PATH 不稳对策，参照 REA 安装经验）。
"""
import os, json, shutil, sys

MCP = r"C:\Users\nczdl\.workbuddy\mcp.json"
BAK = r"C:\Users\nczdl\.workbuddy\mcp.json.bak-20261018-cadgen"
REPORT = r"D:\.AI\GITHUB\trae-dcs-skills\AI任务管理\text-to-cad安装\mcp配置修改_20261018.txt"

UVX = r"C:\Users\nczdl\.local\bin\uvx.exe"
NEW_ENTRY = {
    "type": "stdio",
    "command": UVX,
    "args": ["--no-config", "--managed-python", "--python", "3.13",
             "--from", "cadgen==0.7.21", "cadgen", "mcp"],
    "env": {"CADGEN_INSTALL_CHANNEL": "agent-plugins"},
}

lines = []


def log(s=""):
    lines.append(s)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


log("# mcp.json 修改记录  2026-10-18")
log(f"目标文件: {MCP}")

with open(MCP, "r", encoding="utf-8") as f:
    cfg = json.load(f)

before = cfg.get("mcpServers", {})
before_keys = sorted(before.keys())
log(f"修改前 mcpServers 键({len(before_keys)}): {before_keys}")

if "cadgen" in before:
    log("!! cadgen 条目已存在，中止（不重复添加）")
    print("SKIP")
    sys.exit(0)

shutil.copy2(MCP, BAK)
log(f"已备份: {BAK}  ({os.path.getsize(BAK)} bytes)")

cfg.setdefault("mcpServers", {})["cadgen"] = NEW_ENTRY
with open(MCP, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")

# ---- 自检：重读，JSON 合法 + 原三条逐字保留 ----
with open(MCP, "r", encoding="utf-8") as f:
    cfg2 = json.load(f)
after = cfg2.get("mcpServers", {})
after_keys = sorted(after.keys())
log(f"修改后 mcpServers 键({len(after_keys)}): {after_keys}")

ok = True
for k in before_keys:
    if after.get(k) != before.get(k):
        ok = False
        log(f"!! 原有条目 {k} 被改动！")
log(f"原有 {len(before_keys)} 条逐字保留: {ok}")
log(f"新增条目 cadgen: {json.dumps(after.get('cadgen'), ensure_ascii=False)}")
log("遗留事项: 改后不会自动生效——需用户在 WorkBuddy 自定义连接器页对 cadgen 点'信任'并重开会话")
log(f"结论: {'OK' if ok else 'FAIL'}")
print("OK" if ok else "FAIL")
