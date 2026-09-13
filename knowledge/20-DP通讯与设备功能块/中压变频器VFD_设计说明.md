---
title: 中压变频器VFD功能块设计说明
date: 2026-07-14
project: F163
type: 开发说明
device: 中压变频器
tags: [DP,中压变频器,VFD]
summary: VFD功能块设计说明
source: DP设备资料\中压变频器 - workbuddy\ABB_VFD_FB\设计说明.md
---

# ABB 变频器 Profibus DP 功能块设计说明
# Design Notes — ABB VFD Profibus DP Function Blocks

平台 | Platform: **ABB 800XA V6.1.0** (Control Builder Merra, ST 语言 | Structured Text)
日期 | Date: 2026-07-14

## 0. GSD 文件与通讯模块对照 | GSD & Comm Module Mapping

> **关键 | Key**: 低压与中压变频器使用**不同的 Profibus 通讯适配器模块**,
> 对应不同 GSD 文件 (不同 Ident_Number), 但 PPO 报文结构完全一致。
> LV and MV drives use **different Profibus adapters** (different Ident_Number),
> but PPO telegram structure is identical.

| 变频器类型 | 通讯模块 | Ident | GSD 文件 (DP-V1) | GSD 文件 (DP-V0) | 适用传动 |
|-----------|---------|-------|------------------|------------------|---------|
| 低压 LV | **FPBA-01** | 0x0959 | `ABB10959.gsd` (v2.161+, 2019) | `ABB0959.gsd` | ACS350/ACS550/ACS800/ACS880 |
| 中压 MV | **RPBA-01** | 0x0812 | `ABB10812.GSD` (v1.10, 2005) | `ABB_0812.gsd` | ACS600/ACS1000 等中压平台 |

GSD 文件位置 | GSD file locations:
- 低压 FPBA-01 (新版): `FPBA-01_GSD_files/FPBA-01 v.2161 and later/`
- 中压 RPBA-01: `ABB_Drives_Profibus_DP_control_SimaticS7/GSD/`

**报文一致性 | Telegram compatibility**:
两者 PPO2 均为 `0xF3, 0xF5` (4 PKW + 6 PZD), 数据结构 `VVVFDT` 通用, 功能块逻辑共用。
Both use PPO2 = `0xF3, 0xF5`, VVVFDT structure is shared, FB logic is common.

---

## 1. 文件清单 | File List

| 文件 | File | 说明 | Description |
|------|------|------|-------------|
| `VVVF_DT.st` | — | 通讯数据类型 `VVVFDT` 定义 | Comm data type definition |
| `VFD_LV.st` | — | 低压变频器功能块 `VFD_LV` (ACS550 类) | Low voltage VFD FB |
| `VFD_MV.st` | — | 中压变频器功能块 `VFD_MV` (ACS600/ACS1000 中压类, RPBA-01) | Medium voltage VFD FB |
| `设计说明.md` | — | 本文档 | This document |

输出目录 | Output directory:
`中压变频器 - workbuddy/ABB_VFD_FB/`

---

## 2. 背景与目标 | Background & Objective

原有 `TAYNINH.ACS550` / `TAYNINH.ACS800` 功能块基于旧 GSD 文件开发，采用
FBD(功能块图) + ST 混合编程。本次根据现场 GSD 文件及 FPBA-01/RPBA-01 用户手册
重构为**纯 ST 语言**功能块:

- 低压用 FPBA-01 (0x0959), 中压用 RPBA-01 (0x0812), 两者 PPO 报文结构一致
- 适配 GSD 支持的 PPO 报文类型 (默认 PPO2/4, 6 PZD; FPBA-01 支持 PPO1-8, RPBA-01 支持 PPO1-6)
- 代码全部 ST 实现, 可读性、可维护性优于原 FBD
- 中英文双语注释
- 保持与原功能块接口兼容, 便于工程替换
- 低压/中压分别独立功能块, 适配各自位映射与工艺需求

---

## 3. 报文结构 | Telegram Structure

PPO 类型 (Module 定义) — FPBA-01 支持 PPO1-8, RPBA-01 支持 PPO1-6:

| PPO | PKW | PZD | DP模式 | 字节数 | FPBA-01 | RPBA-01 |
|-----|-----|-----|--------|--------|:-------:|:-------:|
| PPO1 | 4 字 | 2 字 | DP-V0 | 12+4 | ✓ | ✓ |
| PPO2 | 4 字 | 6 字 | DP-V0 | 20+12 | ✓ | ✓ |
| PPO3 | 0 | 2 字 | DP-V0 | 4 | ✓ | ✓ |
| PPO4 | 0 | 6 字 | DP-V0 | 12 | ✓ | ✓ |
| PPO5 | 4 字 | 10 字 | DP-V0 | 28+20 | ✓ | ✓ |
| PPO6 | 0 | 10 字 | DP-V0 | 20 | ✓ | ✓ |
| PPO7 | 4 字 | 12 字 | DP-V0 | 32+24 | ✓ | — |
| PPO8 | 0 | 12 字 | DP-V0 | 24 | ✓ | — |

> **本功能块默认采用 PPO2 (4 PKW + 6 PZD)**, 与原功能块的 6 PZD 结构一致,
> 数据类型 `VVVFDT` 即对应此报文 (6 入 6 出 DINT)。若改用 PPO4 可省略 PKW 参数
> 通道; 改用 PPO6/8 可扩展更多 PZD, 此时需扩展 `VVVFDT` 结构。

### PZD 映射 | PZD Mapping (PPO2/4, 6 PZD)

**IN 区 (Drive → PLC) 变频器→PLC:**

| PZD | 字段 | 含义 |
|-----|------|------|
| PZD1 | SW | 状态字 Status Word |
| PZD2 | ACT1 | 实际值1 频率/速度 Frequency/Speed |
| PZD3 | ACT2 | 实际值2 电流 Current |
| PZD4 | ACT3 | 实际值3 (本地控制位等) |
| PZD5 | ACT4 | 实际值4 功率 Power |
| PZD6 | ACT5 | 实际值5 温度等 Temperature |

**OUT 区 (PLC → Drive) PLC→变频器:**

| PZD | 字段 | 含义 |
|-----|------|------|
| PZD1 | CW | 控制字 Control Word |
| PZD2 | REF1 | 给定1 频率/速度 Frequency/Speed |
| PZD3 | REF2 | 给定2 |
| PZD4 | REF3 | 给定3 |
| PZD5 | REF4 | 给定4 |
| PZD6 | REF5 | 给定5 |

---

## 4. 控制字 / 状态字位定义 | CW / SW Bit Definition

### 控制字 CW (PLC→Drive, PROFIdrive 标准, RPBA-01 手册 Table 7)

| Bit | 名称 | 含义 | 功能块处理 |
|-----|------|------|-----------|
| 0 | On/Off1 | 启动准备 | `drive` 运行命令 |
| 1 | Off2 | =1 不停机, =0 自由停机 | 常置 1 |
| 2 | Off3 | =1 不停机, =0 快速停机 | `NOT EMG_stop` |
| 3 | OPERATION_ENABLE | 运行使能 (Run) | `drive` 延时 500ms 后置位 |
| 4 | Ramp out zero | 斜坡输出加速 | 常置 1 |
| 5 | Ramp hold | 斜坡保持 | 常置 1 |
| 6 | Ramp in zero | 斜坡输入减速 | 常置 1 |
| 7 | Reset | 故障复位 (上升沿) | `Reset` / `RESET1` |
| 10 | Remote | 远程控制 | 常置 1 |

### 状态字 SW (Drive→PLC)

**位定义来源 | Source: RPBA-01 手册 Table 8 / FPBA-01 手册 (PROFIdrive 行规)。
CW/SW 位定义在 PROFIdrive 与 ABB Drives 两种操作模式下通用, 仅 REF 标度不同。**

Table 8 完整位定义 (供参考) | Full Table 8 (reference):

| Bit | 名称 | 含义 |
|-----|------|------|
| 0 | RDY_ON | 准备就绪 Ready to switch on |
| 1 | RDY_RUN | 准备运行 Ready to operate |
| 2 | RDY_REF | 运行使能 Enable operation (≈Run) |
| 3 | TRIPPED | 故障 Fault |
| 4 | OFF_2_STA | Off2 状态 (1=inactive) |
| 5 | OFF_3_STA | Off3 状态 (1=inactive) |
| 6 | SWC_ON_INHIB | 合闸抑制 |
| 7 | ALARM | 报警 Warning/Alarm |
| 8 | AT_SETPOINT | 已达给定 |
| 9 | REMOTE | 远程 (1=Remote) |
| 10 | ABOVE_LIMIT | 超限 |
| 11-15 | — | Drive-specific |

本工程功能块实际使用位 | Bits used by FBs:

| Bit | VFD_LV 低压 (FPBA-01/ACS550) | VFD_MV 中压 (RPBA-01/ACS600/ACS1000) |
|-----|------------------------------|--------------------------------------|
| 0 | RDY_ON/运行 (ACS550 现场配置) | — |
| 2 | — | RDY_REF 运行使能 (Table 8 标准) |
| 3 | TRIPPED 故障 | TRIPPED 故障 |
| 7 | ALARM 报警 | ALARM 报警 |
| 12 | Drive-specific 状态 (LV) | — |

> **操作模式与 REF 标度 | Operation mode & REF scaling** (RPBA-01 P46):
> - **PROFIdrive 模式**: REF 满量程 16384 (4000h) 对应电机额定转速
> - **ABB Drives (Vendor Specific) 模式**: REF 标度由传动决定; 本工程
>   ACS550/ACS800 用 20000 对应 50 Hz, 即采用此模式
> - 由 RPBA-01 参数 930 / FPBA-01 对应参数 + 传动参数组选择
> - **CW/SW 位定义两种模式通用**, 本功能块位映射已对照 Table 7/8 核对确认。

---

## 5. 功能块接口 | Function Block Interface

### 5.1 VFD_LV (低压 | Low Voltage)

**输入参数 | VAR_INPUT**
- `Address` (STRING) — Profibus 地址
- `Group_start` / `Group_stop` (BOOL) — 群组启停
- `EMG_stop` (BOOL) — 急停
- `Start_lock` (BOOL, init TRUE) — 启动联锁, TRUE 才允许启动
- `process_lock` / `safe_lock` (BOOL, init TRUE) — 工艺/安全联锁, FALSE 停机
- `Ext_fault` (BOOL) — 外部故障, TRUE 停机
- `SET_AUTO` (REAL) — 自动给定 Hz
- `K` (REAL, init 1.0) — 反馈系数
- `ZSPSWITCH` (BOOL) — 零速开关
- `READY1` (BOOL, init TRUE) — 外部准备就绪
- `Description` (STRING[60]) — 设备描述

**输入输出 | VAR_IN_OUT**
- `VVVFDINT` (VVVFDT) — Profibus 通讯数据

**输出 | VAR_OUTPUT**
- `READY` / `RUNNING` / `FAULT` (BOOL) — 准备/运行/故障

### 5.2 VFD_MV (中压 | Medium Voltage)

在 VFD_LV 基础上增加:

- `Temp` (DINT, init 0) — 温度传感器类型 0/1/2/3
- `KK` (REAL, init 1.0) — 反馈系数 (替代 K)
- `SET_AUTO` 改为 **in_out** (可被功能块回写, 兼容原 ACS800)

中压特有内部配置 (RETAIN, 可 HMI 调整):
- `set_type` (DINT) — 给定类型 0频率/1速度/2百分比
- `SPEED_MAX` (REAL, 1500) — 最大速度 rpm
- `FEQ_MAX` (REAL, 50) — 最大频率 Hz
- `FEQ_START` (REAL, 5) — 启动频率 Hz
- `temp_Limit` (REAL, 110) — 电机温度限值 ℃
- `R_offset` (REAL) — PT100 偏移电阻

---

## 6. 给定与反馈换算 | Setpoint & Feedback Scaling

### 低压 VFD_LV (ACS550)
```
频率给定:  REF1 = SET_L × 400          (满量程 20000 ↔ 50 Hz)
频率反馈:  Frequency = ACT1 / 400 × K
电流反馈:  Current = ACT2 / 10
功率反馈:  power = ACT4 / 10
```

### 中压 VFD_MV (ACS800/中压)
```
频率给定:  REF1 = SET / FEQ_MAX × 20000 × KK
频率反馈:  Frequency = ACT1 / 20000 × FEQ_MAX × KK
速度反馈:  speed_act = SPEED_MAX × Frequency / FEQ_MAX
百分比:    percent_act = Frequency / FEQ_MAX × 100
电流反馈:  Current = ACT2 / 10
功率反馈:  power = ACT4 / 10
温度(PT100): motor_temp = (ACT5 / 15 − 100 − R_offset) / 0.39083
```

> 低压用 400 (=20000/50) 简化系数; 中压用 20000/FEQ_MAX 表达式, FEQ_MAX 可配置,
> 两者本质相同 (400 × 50 = 20000)。

---

## 7. 与原功能块对应关系 | Mapping to Legacy FB

| 原功能块 | 新功能块 | 主要变化 |
|----------|----------|----------|
| `TAYNINH.ACS550` | `VFD_LV` | FBD→纯ST; 位掩码常量化; 增强注释 |
| `TAYNINH.ACS800` | `VFD_MV` | FBD→纯ST; 增加温度保护联锁; 给定类型可配置 |
| `TAYNINH.VVVFDT` | `VVVFDT` | 结构不变, 增加字段注释 |

**保持兼容 | Preserved:**
- 数据类型 `VVVFDT` 字段名、顺序不变
- 输入/输出参数名基本一致 (SET_AUTO 在中压为 in_out)
- SW/CW 位映射沿用现场验证值
- 事件源名称、报警消息默认值保留

**改进点 | Improvements:**
- 纯 ST 实现, 无 FBD 图形依赖, 便于版本管理与跨工程复用
- CW/SW 位定义用 `VAR CONSTANT` 掩码声明, 现场调整只改常量
- 中压增加电机温度超限延时联锁 (temp_Limit + t5s)
- 状态码 `STATUS` 汇总各诊断位, 便于 HMI 显示
- 注释中英文双语, 便于国际化团队维护

---

## 8. 导入 800XA 工程步骤 | Import to 800XA

1. **数据类型**: 在 800XA Control Builder 的 Data Types 中新建 `VVVFDT`,
   按 `VVVF_DT.st` 添加 12 个 `DIntIO` 组件 (字段名、顺序、注释一致)。
   将 `VVVFDT` 绑定到 Profibus DP 从站的对应 PZD 字 (IN/OUT 区各 6 字)。

2. **功能块**: 在 Function Block Types 中新建 `VFD_LV` / `VFD_MV`:
   - Parameters (参数): 按 `VAR_INPUT` / `VAR_IN_OUT` / `VAR_OUTPUT` 录入,
     注意 Direction (in/out/in_out)、FD Port (yes)、Initial Value、retain 属性。
   - Variables (变量): 按 `VAR` / `VAR RETAIN` / `VAR COLDRETAIN` 录入,
     注意 Attributes (retain / coldretain)、Initial Value。
   - Code: 将功能块体 (FUNCTION_BLOCK Body 部分) 粘贴到 ST 编辑器。
   - 功能块实例 (TP/TOn/TOf/RS/AlarmCond/SimpleEventDetector/TimerU/F_Trig)
     需在 Variables 中预先声明为对应系统功能块类型。

3. **GSD 安装** (区分低压/中压 | separate for LV/MV):
   - 低压: 安装 `ABB10959.gsd` (DP-V1) 或 `ABB0959.gsd` (DP-V0), 硬件组态选
     **FPBA-01** (Ident 0x0959), 模块选 **PPO-02** (4 PKW + 6 PZD)。
   - 中压: 安装 `ABB10812.GSD` (DP-V1) 或 `ABB_0812.gsd` (DP-V0), 硬件组态选
     **RPBA-01** (Ident 0x0812), 模块选 **PPO Type 2** (4 PKW + 6 PZD)。
   - 对应 bmp/ico 图标文件一并安装到 800XA Profibus 配置工具的 GSD 目录。

4. **变频器侧配置**: 设置变频器的 Profibus 参数组 (低压 ACS550 第 53 组 /
   中压 ACS600/ACS1000 对应参数组), 使 PZD 映射与本功能块一致
   (PZD1=CW/SW, PZD2=REF1/ACT1 频率, …)。

---

## 9. 配置要点 | Configuration Notes

- **PPO 选择**: 默认 PPO2 (带 PKW 参数通道); 若无需周期性读写变频器参数,
  可选 PPO4 (纯过程数据), 功能块代码不需改动 (PKW 由 800XA 硬件层处理)。

- **SW 位调整**: 若现场变频器 53 组参数改了位映射, 修改功能块顶部
  `VAR CONSTANT` 的 `SW_MSK_*` 掩码即可, 无需改逻辑代码。

- **本地升降键**: 低压用 ACT3.B2(升)/ACT4.B2(降); 中压用 ACT3.B2(升)/ACT3.B3(降)。
  若现场按键映射不同, 修改给定处理段的位掩码。

- **温度传感器 (中压)**: `Temp` 参数 = 3 时按 PT100 公式换算, 需标定 `R_offset`
  偏移电阻; =1/2 时 ACT5 直接为温度值; =0 时关闭温度监测。

- **运行时间**: `TimerU` 累计运行时间存于 `RN_TIME`, 可通过 `T_RST` 复位、
  `M_PT` 预置。`M_PT` 为 retain, 掉电保持。

- **给定类型 (中压)**: `set_type` 决定主给定源: 0=频率(Hz)、1=速度(rpm)、
  2=百分比(%)。HMI 可切换模式, 功能块自动换算其余两个量。

---

## 10. 参考 | References

- `FPBA01_CN_revC.pdf` — FPBA-01 PROFIBUS DP 适配器模块用户手册 (中文, 低压)
- `EN_FPBA01_UM_E.pdf` — FPBA-01 User's Manual (English, 低压)
- `ABB10959.gsd` / `ABB0959.gsd` — FPBA-01 GSD (Ident 0x0959, 低压, v2.161+)
- `RPBA01_MANUAL.pdf` — RPBA-01 PROFIBUS DP Adapter Module User's Manual (中压)
- `ABB10812.GSD` / `ABB_0812.gsd` — RPBA-01 GSD (Ident 0x0812, 中压)
- `ABB drives and Siemens PLC integration using PROFIBUS DP - ABB_DRIVES_LIB Quickstart Guide RevA.pdf`
- 原 `TAYNINH.ACS550` / `TAYNINH.ACS800` 功能块 (ACS550_CODE*.pdf / ACS800_CODE*.pdf, 逻辑参考)
