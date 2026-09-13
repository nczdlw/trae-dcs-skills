---
title: 中压变频器FB开发规则2
date: 2026-07-15
project: F163
type: 规则
device: 中压变频器
tags: [DP,中压变频器,开发规则]
summary: 中压变频器功能块开发规则第2版
source: DP设备资料\中压变频器 - trae\新功能块\ABB_800XA_FB开发规则2.md
---

# ABB 800XA V6.1.0 功能块开发规则与经验总结

> 基于 越南F163粉磨站 ABB_LV_VVVF / ABB_MV_VVVF 功能块开发过程中遇到的所有编译错误和修复经验整理。
> 日期：2026-07-15

---

## 一、变量命名规则

### 1.1 大小写不敏感
800XA 编译器对变量名**大小写不敏感**，以下被视为同名变量（Error 1000）：
- `Local_permission` = `LOCAL_PERMISSION` = `local_permission`

**规则**：同一功能块内，变量名不能仅靠大小写区分。如需相似名称，必须改变拼写（如 `LOCAL_PERM`）。

### 1.2 VAR 与 PAR 全局唯一
变量名必须在 **VAR 表和 PAR 表合并后**全局唯一，不能在两张表中同时声明同名变量。

**反面案例**：`SET_AUTO` 同时出现在 VAR 和 PAR 中 → Error 1000。

**规则**：一个变量只在一处声明。既要在代码中读又要写的参数，放在 PAR 中，方向设为 `in_out`，不要在 VAR 中重复声明。

### 1.3 in_out 方向不能带 retain
`in_out`（by_ref）方向的参数不能使用 `retain` 属性（Error 1005）。

```
❌ SET_AUTO  real  retain  in_out  yes
✅ SET_AUTO  real          in_out  yes
```

### 1.4 in 方向不能在代码中赋值
`in` 方向的参数是只读的，在 ST 代码中对其赋值会报 Error 1034。

```
❌ PAR: SET_AUTO  real  in    （代码中 SET_AUTO := SET_A 报错）
✅ PAR: SET_AUTO  real  in_out（允许读写）
```

---

## 二、标准功能块引脚名

### 2.1 引脚名速查表

| FB 类型 | Set 引脚 | Reset 引脚 | 输出引脚 | 定时器输入 |
|---------|----------|-----------|----------|-----------|
| **RS** | `Set` | `R1` | `Q1` | — |
| **SR** | `S1` | `Reset` | `Q1` | — |
| **TOn** | — | — | `Q` | `In`, `PT` |
| **TOf** | — | — | `Q` | `In`, `PT` |
| **TP** | — | — | `Q` | `In`, `PT` |
| **F_Trig** | — | — | `Q` | `Clk` |
| **R_Trig** | — | — | `Q` | `Clk` |

### 2.2 易错点

| 错误写法 | 正确写法 | 说明 |
|----------|----------|------|
| `RS_1(Reset1 := ...)` | `RS_1(R1 := ...)` | RS 复位引脚是 `R1` 不是 `Reset1` |
| `SR_1(R1 := ...)` | `SR_1(Reset := ...)` | SR 复位引脚是 `Reset` 不是 `R1` |
| `SR_1(R := ...)` | `SR_1(Reset := ...)` | SR 复位引脚是 `Reset` 不是 `R` |
| `TOn_1(IN := ...)` | `TOn_1(In := ...)` | 定时器输入是 `In`（首字母大写）不是 `IN` |
| `F_Trig_2(IN := ...)` | `F_Trig_2(Clk := ...)` | 触发器输入是 `Clk` 不是 `IN` |

### 2.3 引脚名大小写敏感
虽然变量名大小写不敏感，但 **FB 引脚名是大小写敏感**的：
- `In` ✅ （不是 `IN`）
- `Set` ✅ （不是 `SET`）
- `Clk` ✅ （不是 `CLK`）

---

## 三、自定义功能块（TAYNINH 库）

### 3.1 Dint_bool16 / BOOL16_DINT

TAYNINH 库中的自定义类型与标准 `DINTTOBOOL16`/`BOOL16TODINT` **完全不同**：

| 特性 | 标准 DINTTOBOOL16 | TAYNINH Dint_bool16 |
|------|-------------------|---------------------|
| 输入 | `Int` (DINT) | `in` (DINT) |
| 输出 | `BoolStruct` (Boolean16) + `Status` (DINT) | `bool0`~`bool15` (16个独立 bool) |

| 特性 | 标准 BOOL16TODINT | TAYNINH BOOL16_DINT |
|------|-------------------|---------------------|
| 输入 | `BoolStruct` (Boolean16) | `IN0`~`IN15` (16个独立 bool) |
| 输出 | `Int` (DINT) + `Status` (DINT) | `OUT` (DINT) |

### 3.2 调用示例

```pascal
(* Dint_bool16: DINT → 16个独立bool *)
Dint_bool16_1(
    in := VVVFDINT.INPUTDINT1.Value,
    bool0 => INBOOL1_B0,
    bool1 => INBOOL1_B1,
    ...
    bool15 => INBOOL1_B15);

(* BOOL16_DINT: 16个独立bool → DINT *)
BOOL16_DINT_1(
    IN0 := OUTBOOL1_B0,
    IN1 := OUTBOOL1_B1,
    ...
    IN15 := OUTBOOL1_B15,
    OUT => VVVFDINT.OUTPUTDINT1.Value);
```

### 3.3 变量声明变化
使用 TAYNINH 自定义类型后，不再需要：
- `Boolean16` 类型变量（改为 16 个独立 `bool`）
- `_STA` 状态变量（自定义类型无 Status 输出）

```
❌ INBOOL1  Boolean16         →  ✅ INBOOL1_B0~B15  bool (16个)
❌ INBOOL1_STA  dint          →  （删除，用 VVVFDINT.INPUTDINT1.Value 代替）
```

### 3.4 还有 Dint_bool32 / BOOL32_DINT
TAYNINH 库中还包含 32 位版本，引脚结构类似（`bool0`~`bool31` / `IN0`~`IN31`）。

---

## 四、ST 代码语法规则

### 4.1 禁止尾随逗号
800XA ST 不允许函数调用最后一个参数后带逗号（Error 1104 / 1116）。

```pascal
❌ bool15 => INBOOL1_B15,
   );

✅ bool15 => INBOOL1_B15);
```

### 4.2 最后一个参数与 ); 必须同行
`);` 不能单独一行，必须跟在最后一个参数后面（Error 1023）。

```pascal
❌ bool15 => INBOOL1_B15
   );

✅ bool15 => INBOOL1_B15);
```

### 4.3 多参数调用格式
参数间用逗号分隔，最后一个参数无逗号，`);` 紧跟最后参数：

```pascal
BOOL16_DINT_1(
    IN0 := OUTBOOL1_B0,
    IN1 := OUTBOOL1_B1,
    ...
    IN15 := OUTBOOL1_B15,
    OUT => VVVFDINT.OUTPUTDINT1.Value);
```

---

## 五、FUN 表规则

### 5.1 所有 FB 实例必须在 FUN 表中声明
ST 代码中调用的每个 FB 实例（包括 `Dint_bool16`、`BOOL16_DINT`）都必须在 FUN 表中声明，否则报 Error 1023 "Undefined function block"。

> **注意**：老代码（ACS550/ACS800）使用 FBD 图形方式，这些 FB 在 FUN 中没有声明是因为 FBD 自动处理。ST 代码方式必须手动声明。

### 5.2 FUN 表中不能有未使用的实例
FUN 表中声明但 ST 代码中未调用的 FB 会产生 Warning 1542。应删除未使用的实例。

### 5.3 FUN 表格式

| 序号 | 实例名 | FB类型 | 任务连接 | 描述 |
|------|--------|--------|----------|------|
| 1 | Dint_bool16_1 | Dint_bool16 | | |
| 2 | TP_1 | TP | | |
| 3 | RS_1 | RS | | |

---

## 六、Excel 文件格式规则

### 6.1 严格遵循老功能块格式
VAR/PAR/FUN 表的格式必须与老功能块（ACS550/ACS800）完全一致：
- 第1行：合并标题行 `Function Block Type - TAYNINH.xxx - Variables/Parameters/Function Blocks`
- 第2行：列头
- 数据行：序号 + 内容
- 最后行：日期 + 页码（如 `2026-07-14 20:09  - 1 -`）

### 6.2 列结构

| 文件 | 列 |
|------|-----|
| **VAR** | 序号, Name, Data Type, Start Attribute, Attributes, Initial Value, Description |
| **PAR** | 序号, Name, Data Type, Start Attribute, Attributes, Direction, FD Port, Initial Value, Description |
| **FUN** | 序号, Name, Function Block Type, Task Connection, Description |

### 6.3 Direction 值（仅 PAR）
- `in` — 只读输入
- `out` — 只写输出
- `in_out` — 读写（既读又写）

### 6.4 Start Attribute 值
- `retain` — 保持型
- `coldretain` — 冷保持型
- 空 — 无属性

---

## 七、数据类型与换算

### 7.1 VVVFDT 数据类型
共享数据类型，包含 6 输入 DINT + 6 输出 DINT：

| 成员 | PPO4 映射 | 说明 |
|------|-----------|------|
| INPUTDINT1 | PZD1 (SW) | 状态字 |
| INPUTDINT2 | PZD2 (ACT1) | 实际值1（频率） |
| INPUTDINT3 | PZD3 (ACT2) | 实际值2（电流） |
| INPUTDINT4 | PZD4 (ACT3) | 实际值3 |
| INPUTDINT5 | PZD5 (ACT4) | 实际值4（功率） |
| INPUTDINT6 | PZD6 (ACT5) | 实际值5（温度，MV专用） |
| OUTPUTDINT1 | PZD1 (CW) | 控制字 |
| OUTPUTDINT2 | PZD2 (REF1) | 给定值1（频率） |
| OUTPUTDINT4 | PZD4 (REF3) | 给定值3（控制位） |

### 7.2 换算系数

| 信号 | 换算 | 说明 |
|------|------|------|
| 频率 REF/ACT | 20000 = 100% = Freq_Max | ABB Drives 行规 |
| 电流 ACT | 10 = 1A | 驱动参数映射 |
| 功率 ACT | 10 = 1kW | 驱动参数映射 |
| 温度 ACT | 10 = 1°C | MV专用 |

---

## 八、通信行规

### 8.1 FPBA-01（低压）
- GSD: `ABB10959.gsd`，Ident: `0x0959`
- 默认 ABB Drives 行规（20000=100%）
- 参数 51.27 = 0 → ABB Drives，51.27 = 1 → PROFIdrive

### 8.2 RPBA-01（中压）
- GSD: `ABB10812.GSD`，Ident: `0x0812`
- 默认 PROFIdrive 行规（20000=100%）

### 8.3 控制字（CW）关键位

| Bit | 名称 | 说明 |
|-----|------|------|
| 0 | OFF1 | 1=运行，0=斜坡停车 |
| 1 | OFF2 | 1=运行，0=自由停车 |
| 2 | OFF3 | 1=运行，0=快速急停 |
| 3 | OPERATION_ENABLE | 1=允许运行 |
| 7 | RESET | 0→1 故障复位 |
| 10 | REMOTE_CMD | 1=总线控制使能 |

### 8.4 状态字（SW）关键位

| Bit | 名称 | 说明 |
|-----|------|------|
| 0 | RDY_ON | 1=准备合闸 |
| 1 | RDY_RUN | 1=准备操作 |
| 2 | RDY_REF | 1=允许运行 |
| 3 | TRIPPED | 1=故障 |
| 7 | ALARM | 1=警告 |
| 8 | AT_SETPOINT | 1=运行中（达到给定） |
| 9 | REMOTE | 1=远程控制 |

### 8.5 CW 十六进制值

| 命令 | 值 | 说明 |
|------|-----|------|
| STOP/Ready | `0x047E` | bit0=0 |
| RUN | `0x047F` | bit0=1 |
| Fault Reset | `0x04FE` | bit7=1，然后回 `0x047E` |
| EMG Stop | `0x043E` | bit2=0 |

---

## 九、LV 与 MV 功能块差异

| 特性 | ABB_LV_VVVF (低压) | ABB_MV_VVVF (中压) |
|------|--------------------|--------------------|
| 通信模块 | FPBA-01 | RPBA-01 |
| GSD文件 | ABB10959.gsd | ABB10812.GSD |
| 适用驱动 | ACS355/ACSM1/ACS850/ACQ810/ACS880 | ACS600/ACS800/ACS1000/ACS5000/DCS800 |
| 行规 | ABB Drives | PROFIdrive |
| 电机温度监控 | 无 | 有（motor_temp, temp_Limit, TEMP_ALARM） |
| 控制模式 | 仅频率 | 频率/转速/百分比（set_type） |
| 急停定时器 | 无 | 有（TOf_1, ES_TIME） |
| Dint_bool16 实例数 | 2 | 3 |
| 报警数量 | 4 | 6 |

---

## 十、开发流程检查清单

### 10.1 编码前
- [ ] 确认 GSD 文件和通信模块型号（FPBA-01 vs RPBA-01）
- [ ] 确认通信行规（ABB Drives vs PROFIdrive）和换算系数
- [ ] 读取老功能块代码，确认 FB 引脚名和变量命名规范
- [ ] 确认 TAYNINH 库中可用的自定义 FB 类型及其引脚定义

### 10.2 编码中
- [ ] 变量名在 VAR+PAR 合并后全局唯一（注意大小写不敏感）
- [ ] `in_out` 方向不带 `retain`
- [ ] `in` 方向不在代码中赋值
- [ ] 所有 FB 引脚名使用正确大小写（`In` 不是 `IN`，`R1` 不是 `Reset1`）
- [ ] 使用 `Dint_bool16`/`BOOL16_DINT` 时拆分为 16 个独立 bool
- [ ] ST 函数调用无尾随逗号
- [ ] `);` 与最后一个参数同行

### 10.3 编码后
- [ ] FUN 表中声明所有 ST 代码中调用的 FB 实例
- [ ] FUN 表中无未使用的 FB 实例
- [ ] VAR 表中无与 PAR 重复的变量
- [ ] VAR 表中无 Boolean16 类型（如使用 TAYNINH 自定义 FB）
- [ ] Excel 文件格式与老功能块一致
- [ ] 所有文件导入 800XA 后编译通过

---

## 十一、常见错误速查

| 错误码 | 含义 | 常见原因 |
|--------|------|----------|
| 1000 | 变量名不唯一 | VAR/PAR 重复声明；大小写不敏感冲突 |
| 1002 | FB 类型未找到 | 自定义 FB 未导入；类型名拼写错误 |
| 1005 | retain 不允许 | in_out 方向带了 retain |
| 1023 | 未定义 FB 实例 | FUN 表中未声明该实例 |
| 1024 | 未定义 FB 参数 | 引脚名错误（如 Reset1 vs R1） |
| 1032 | 变量未声明 | 代码中使用了 VAR/PAR 中不存在的变量 |
| 1034 | 不允许修改 | in 方向参数在代码中被赋值 |
| 1104 | 缺少表达式 | 尾随逗号 |
| 1116 | 缺少标识符 | 逗号缺失或多余 |
| 1542 | FB 未调用（警告） | FUN 表中有多余的未使用实例 |
