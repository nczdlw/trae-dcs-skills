# DCS 自动编程调试框架（dcs-auto-framework）

面向水泥项目主流 DCS（ABB 800xA / 西门子 PCS7 / ABB Freelance）的自动编程调试框架。
本框架在现有 DCS 项目全流程总纲（P1-P6）+ knowledge 体系之上扩展，先打通 800xA，PCS7/Freelance 标"待核实"。

## 目录结构

```
dcs-auto-framework/
├── dcsaf/                  # Python 包
│   ├── ir/                 # 统一中间表示（IR）
│   │   ├── point_table.py  # 点位表模型 + 校验器
│   │   ├── logic_model.py  # 功能块逻辑模型 + 校验器
│   │   ├── io.py           # IR 读写（YAML/JSON）
│   │   ├── diff.py         # IR diff
│   │   └── version.py      # 版本目录管理
│   ├── profiles/           # 平台 Profile（模板/功能块库/格式定义）
│   ├── adapters/           # 平台 Adapter（IR ↔ 平台格式）
│   └── tools/              # 横向工具（OPC UA / 快速响应 / 字节序 / 仿真）
├── profiles/               # 平台模板与功能块库数据文件
├── libs/                   # 各平台功能块库（YAML）
├── tools/                  # 独立工具脚本
├── docs/                   # 文档
└── samples/                # 示例素材
```

## 使用

```bash
pip install -r requirements.txt
python -m dcsaf.cli --help
```
