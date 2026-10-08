# -*- coding: utf-8 -*-
"""800xA Adapter：IR ↔ 800xA 导入/导出表（VAR 表 / FUN 表）。

T4 任务产物，实现 IR（统一中间表示）与 ABB 800xA 批量导入表之间的
双向转换与增量去重：

- generate_var_excel : 点位表 IR → 800xA VAR 表 xlsx（7 列）
- generate_fun_excel : 逻辑 IR    → 800xA FUN 表 xlsx（5 列，校验功能块类型）
- parse_800xa_export : VAR/FUN xlsx → IR（回读解析，列名大小写不敏感、跳过空行）
- dedupe_increment   : 增量去重（变量名/实例名唯一键，忽略大小写、去首尾空格）

约束与依据：
- 列定义严格取自 profiles/io_templates/ab800xa_io_template.yaml 的 VAR./FUN.
  段列（表头去掉段前缀），禁止凭空增加模板中不存在的列；
- 功能块类型校验取自 libs/ab800xa_fb_library.yaml（28 类，类型名大小写敏感，
  如 TOf / R_Trig / AlarmCond）；
- 去重规则取自 knowledge/40-变量与功能块规范/ABB800xA_VAR_FUN对比与导入规则.md
  （变量名/实例名唯一键，忽略大小写、去首尾空格；增量表=设计所需−现场已有）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from openpyxl import Workbook, load_workbook

from ..ir import Fb, LogicProgram, Point, PointTable

# 框架根目录（dcs-auto-framework）
ROOT = Path(__file__).resolve().parent.parent.parent
# 800xA IO 表格模板（列定义基准，只读）
AB800XA_TEMPLATE_PATH = ROOT / "profiles" / "io_templates" / "ab800xa_io_template.yaml"
# 800xA 功能块库（类型校验基准，只读）
AB800XA_FB_LIBRARY_PATH = ROOT / "libs" / "ab800xa_fb_library.yaml"

# IR signal_type → VAR 表 Data Type 基础映射。
# 依据：任务明确 DI→bool、DO→bool、AI→real、AO→real；模板 VAR.Data Type 列
# 描述同义（DI/DO→bool、AI/AO→Real，硬件直访可带 IO 后缀 BoolIO/RealIO），
# 本函数采用基础类型，IO 后缀变体留给工程化配置。
SIGNAL_TO_VAR_TYPE = {"DI": "bool", "DO": "bool", "AI": "real", "AO": "real"}

# VAR 表 Data Type → IR signal_type 反向映射（回读解析）。
# 文档明确映射：bool→DI、real→AI；模板明确"硬件 I/O 映射带 IO 后缀"，
# 故 BoolIO/RealIO 一并映射。注意：VAR 表只有 Data Type、无方向信息，
# DO/AO 无法还原，回读一律按输入侧 DI/AI 处理（信息丢失，调用方需知悉）。
VAR_TYPE_TO_SIGNAL = {
    "bool": "DI", "real": "AI",
    "boolio": "DI", "realio": "AI",
}


# ---------------------------------------------------------------------------
# 模板 / 功能块库读取（只读，不修改基准文件）
# ---------------------------------------------------------------------------

def _load_io_template() -> Dict[str, Any]:
    """读取 800xA IO 表格模板 YAML。"""
    if not AB800XA_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"800xA IO 模板不存在: {AB800XA_TEMPLATE_PATH}")
    with open(AB800XA_TEMPLATE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_fb_library() -> Dict[str, Any]:
    """读取 800xA 功能块库 YAML。"""
    if not AB800XA_FB_LIBRARY_PATH.exists():
        raise FileNotFoundError(f"800xA 功能块库不存在: {AB800XA_FB_LIBRARY_PATH}")
    with open(AB800XA_FB_LIBRARY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _segment_columns(template: Dict[str, Any], segment: str) -> List[Dict[str, Any]]:
    """取模板中指定段（'VAR.' / 'FUN.'）的列定义，保持模板原有顺序。"""
    return [c for c in template.get("columns", [])
            if str(c.get("name", "")).startswith(segment)]


def _header_names(cols: List[Dict[str, Any]], segment: str) -> List[str]:
    """去掉段前缀生成表头（如 'VAR.Name' → 'Name'，对应 800xA 导入表实际列名）。"""
    return [str(c["name"])[len(segment):] for c in cols]


# ---------------------------------------------------------------------------
# 生成 VAR 表 / FUN 表
# ---------------------------------------------------------------------------

def generate_var_excel(point_table_ir: PointTable, output_path: str) -> str:
    """点位表 IR → 800xA VAR 表 xlsx（7 列：序号/Name/Data Type/Start Attribute/Attributes/Initial Value/Description）。

    列定义从 ab800xa_io_template.yaml 的 VAR. 段读取（表头去掉 'VAR.' 前缀）。
    每个 Point 映射一行：
    - Name = tag（位号，唯一键）
    - Data Type 按 signal_type 映射（DI/DO→bool、AI/AO→real）
    - Description = description
    Start Attribute / Attributes / Initial Value 为模板平台专有列
    （ir_field=null，IR 无对应字段），留空不编造。
    返回输出路径。
    """
    template = _load_io_template()
    var_cols = _segment_columns(template, "VAR.")
    if not var_cols:
        raise ValueError(f"模板 {AB800XA_TEMPLATE_PATH.name} 中无 VAR. 段列定义")

    wb = Workbook()
    ws = wb.active
    ws.title = "VAR"
    ws.append(_header_names(var_cols, "VAR."))
    for idx, p in enumerate(point_table_ir.points, start=1):
        ws.append([
            idx,                                               # 序号
            p.tag,                                             # Name = 位号
            SIGNAL_TO_VAR_TYPE.get(p.signal_type, p.signal_type),  # Data Type
            "",                                                # Start Attribute（平台列，无映射）
            "",                                                # Attributes（平台列，无映射）
            "",                                                # Initial Value（平台列，无映射）
            p.description or "",                               # Description
        ])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def generate_fun_excel(logic_program_ir: LogicProgram, output_path: str) -> List[str]:
    """逻辑 IR → 800xA FUN 表 xlsx（5 列：序号/Name/Function Block Type/Task Connection/Description）。

    列定义从 ab800xa_io_template.yaml 的 FUN. 段读取（表头去掉 'FUN.' 前缀）。
    每个 Fb 映射一行：
    - Name = instance（实例名，唯一键）
    - Function Block Type = ftype
    - Description = comment
    Task Connection 为模板平台专有列（ir_field=null，IR 无对应字段），留空。
    按功能块库（libs/ab800xa_fb_library.yaml）校验 ftype 是否在库中
    （类型名大小写敏感，800xA 类型名如 TOf / R_Trig 区分大小写），
    不在库中的类型收集到返回的警告列表。
    返回警告列表（空列表表示全部类型在库中）。
    """
    template = _load_io_template()
    fun_cols = _segment_columns(template, "FUN.")
    if not fun_cols:
        raise ValueError(f"模板 {AB800XA_TEMPLATE_PATH.name} 中无 FUN. 段列定义")
    library = _load_fb_library()
    lib_types = set(library.get("fbs", {}).keys())

    warnings: List[str] = []
    wb = Workbook()
    ws = wb.active
    ws.title = "FUN"
    ws.append(_header_names(fun_cols, "FUN."))
    for idx, fb in enumerate(logic_program_ir.fbs, start=1):
        if fb.ftype not in lib_types:
            warnings.append(
                f"FUN 表第{idx}行：实例 '{fb.instance}' 类型 '{fb.ftype}' "
                f"不在 800xA 功能块库（{AB800XA_FB_LIBRARY_PATH.name}）中，请核实"
            )
        ws.append([
            idx,                  # 序号
            fb.instance,          # Name = 实例名
            fb.ftype,             # Function Block Type
            "",                   # Task Connection（平台列，无映射）
            fb.comment or "",     # Description
        ])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return warnings


# ---------------------------------------------------------------------------
# 回读解析（800xA 导出 xlsx → IR）
# ---------------------------------------------------------------------------

def _norm(s: Any) -> str:
    """表头/取值规范化：去首尾空格、忽略大小写。"""
    return str(s or "").strip().lower()


def _strip_segment(h: str) -> str:
    """剥离段前缀（'var.' / 'fun.'），兼容带前缀的导出表头。"""
    for prefix in ("var.", "fun."):
        if h.startswith(prefix):
            return h[len(prefix):]
    return h


def _find_column(headers: List[str], candidates: List[str]) -> int:
    """按列名（大小写不敏感、可带段前缀）定位列下标，找不到则报错。"""
    for cand in candidates:
        key = _norm(cand)
        for i, h in enumerate(headers):
            if _strip_segment(_norm(h)) == key:
                return i
    raise ValueError(f"找不到列 {candidates}，实际表头：{headers}")


def _read_sheet_rows(path: str) -> List[Tuple[Any, ...]]:
    """读取 xlsx 第一个工作表全部行（含表头）。"""
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    return list(ws.iter_rows(values_only=True))


def _find_header_row(rows: List[Tuple[Any, ...]]) -> int:
    """定位表头行（第一个非空行）下标。"""
    for i, r in enumerate(rows):
        if any(_norm(v) for v in r):
            return i
    raise ValueError("表格为空，无表头行")


def parse_800xa_export(var_xlsx_path: str, fun_xlsx_path: str) -> Tuple[PointTable, LogicProgram]:
    """解析 800xA 导出的 VAR/FUN xlsx 为 IR 对象。

    文档明确映射：
    - VAR 表：Name 列 → Point.tag；Data Type 列 → signal_type
      （bool→DI、real→AI、BoolIO→DI、RealIO→AI，大小写/空格不敏感）；
      Description 列 → Point.description。
    - FUN 表：Name 列 → Fb.instance；Function Block Type 列 → Fb.ftype；
      Description 列 → Fb.comment。

    容错：列名大小写不敏感、表头可带 VAR./FUN. 段前缀、跳过空行（Name 为空）。

    信息丢失说明（不编造字段）：
    - VAR 表仅含 Data Type、无方向信息，DO/AO 点回读会落为 DI/AI；
    - FUN 表不含管脚/参数信息，回读 Fb 的 pins/params 为空；
    - 量程/单位/报警/分组/DP 等字段在 VAR 表无对应列，回读为空。
    PointTable.name / LogicProgram.name 用文件名 stem 填充（表内无名称列）。
    """
    # ---- VAR 表 ----
    rows = _read_sheet_rows(var_xlsx_path)
    header_idx = _find_header_row(rows)
    headers = [str(v or "") for v in rows[header_idx]]
    col_name = _find_column(headers, ["Name", "名称"])
    col_type = _find_column(headers, ["Data Type", "数据类型"])
    col_desc = _find_column(headers, ["Description", "描述"])

    points: List[Point] = []
    for r in rows[header_idx + 1:]:
        name = str(r[col_name] or "").strip()
        if not name:
            continue  # 跳过空行
        raw_type = r[col_type]
        signal_type = VAR_TYPE_TO_SIGNAL.get(_norm(raw_type), str(raw_type or "").strip())
        points.append(Point(
            tag=name,
            signal_type=signal_type,
            description=str(r[col_desc] or "").strip(),
        ))

    # ---- FUN 表 ----
    fun_rows = _read_sheet_rows(fun_xlsx_path)
    fun_header_idx = _find_header_row(fun_rows)
    fun_headers = [str(v or "") for v in fun_rows[fun_header_idx]]
    f_name = _find_column(fun_headers, ["Name", "名称"])
    f_type = _find_column(fun_headers, ["Function Block Type", "功能块类型"])
    f_desc = _find_column(fun_headers, ["Description", "描述"])

    fbs: List[Fb] = []
    for r in fun_rows[fun_header_idx + 1:]:
        name = str(r[f_name] or "").strip()
        if not name:
            continue  # 跳过空行
        fbs.append(Fb(
            instance=name,
            ftype=str(r[f_type] or "").strip(),
            comment=str(r[f_desc] or "").strip(),
        ))

    table = PointTable(name=Path(var_xlsx_path).stem, points=points)
    program = LogicProgram(name=Path(fun_xlsx_path).stem, fbs=fbs)
    return table, program


# ---------------------------------------------------------------------------
# 增量去重工具
# ---------------------------------------------------------------------------

def _item_key(item: Any) -> str:
    """提取唯一键：字符串直接用；对象取 tag/instance/name 属性；都无则字符串化。"""
    if isinstance(item, str):
        return _norm(item)
    for attr in ("tag", "instance", "name"):
        if hasattr(item, attr):
            return _norm(getattr(item, attr))
    return _norm(str(item))


def dedupe_increment(new_items: List[Any], existing_items: List[Any]) -> Tuple[List[Any], List[Any]]:
    """增量去重：返回 (增量项, 重复项)。

    规则（knowledge/40-变量与功能块规范/ABB800xA_VAR_FUN对比与导入规则.md）：
    - 变量名/实例名是唯一键，比较时忽略大小写、去掉名称前后空格；
    - 增量表 = 设计所需 − 现场已有：new_items 中与 existing_items 同名
      （规范化后相等）的项判为重复；
    - 增量内部不得重复：new_items 内第二次及以后出现的同名项判为重复。

    existing_items 为现场已有清单。名称为空的项按重复处理（需人工复核）。
    返回的两份清单保持 new_items 中的原对象/原字符串。
    """
    existing_keys = {_item_key(x) for x in existing_items}
    seen: set = set()
    added: List[Any] = []
    dup: List[Any] = []
    for item in new_items:
        key = _item_key(item)
        if not key or key in existing_keys or key in seen:
            dup.append(item)
        else:
            seen.add(key)
            added.append(item)
    return added, dup


class AB800xAAdapter:
    """800xA 适配器类接口（T5 基类约定，包装 T4 模块函数）。

    提供与 PCS7/Freelance 桩一致的类方法形态，内部委托模块级函数实现：
    - generate_point_table → generate_var_excel
    - generate_logic       → generate_fun_excel
    - parse_export         → parse_800xa_export
    - dedupe               → dedupe_increment
    """

    platform = "ab800xa"

    def __init__(self, output_dir: str = "") -> None:
        self.output_dir = output_dir

    @staticmethod
    def pending_items() -> List[Dict[str, str]]:
        return [
            {
                "item": "800xA 虚拟控制器 OPC UA 强制功能",
                "status": "待核实",
                "question": "真实虚拟控制器接入细节见 dcsaf/tools/simulator.py 调研登记。",
            },
            {
                "item": "BDM 批量导入列定义",
                "status": "待核实",
                "question": "knowledge 中未找到 BDM 官方列依据，模板 export_format 已注明待补充。",
            },
        ]

    def generate_point_table(self, ir: PointTable) -> str:
        """由 IR 点位表生成 800xA VAR 表 xlsx，返回文件路径。"""
        if self.output_dir:
            from pathlib import Path as _Path
            _Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            out = str(_Path(self.output_dir) / f"{ir.name or 'point'}_Var.xlsx")
        else:
            out = f"{ir.name or 'point'}_Var.xlsx"
        return generate_var_excel(ir, out)

    def generate_logic(self, ir: LogicProgram) -> str:
        """由 IR 逻辑生成 800xA FUN 表 xlsx，返回文件路径。"""
        if self.output_dir:
            from pathlib import Path as _Path
            _Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            out = str(_Path(self.output_dir) / f"{ir.name or 'logic'}_Fun.xlsx")
        else:
            out = f"{ir.name or 'logic'}_Fun.xlsx"
        generate_fun_excel(ir, out)
        return out

    def parse_export(self, path: str) -> Any:
        """解析 800xA 导出文件为 IR。path 可为 VAR xlsx 路径或 (VAR,FUN) 元组。"""
        if isinstance(path, tuple):
            var_path, fun_path = path
        else:
            var_path, fun_path = path, None
        return parse_800xa_export(var_path, fun_path)

    def dedupe(self, increment: Any, existing: Any) -> Any:
        """增量去重，返回 (增量项, 重复项)。"""
        return dedupe_increment(increment, existing)
