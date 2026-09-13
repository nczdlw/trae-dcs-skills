---
title: 莱歇磨FBD程序架构说明
date: 2026-07-10
project: F163
type: 实施说明
tags: [莱歇磨,FBD,架构]
summary: 莱歇磨FBD程序架构说明
source: DP设备资料\莱歇磨 - trae\FBD程序架构说明.md
---

# F163粉磨站水泥磨FBD程序架构说明

## 1. 项目概述
- **项目名称**: Tay Ninh 2 CS - LM 46.2+2 水泥磨系统
- **控制系统**: ABB 800XA with logi.cals
- **程序标准**: IEC 61131-3
- **参考文档**: 最新连锁关系 (Drawing.-Nr. 12893, Fct-Nr. 1602)
- **参考程序**: 老线水泥磨程序 (NINH_3E8.CementMill)

## 2. 程序结构

### 2.1 主程序组 (Main Groups)
| 组号 | 名称 | 描述 |
|------|------|------|
| G00 | Main Group AUX | 辅助设备主组 |
| G01 | Group Heater | 加热器组 |
| G03 | Mill Gearbox Lubrication | 磨机齿轮箱润滑 |
| G10 | HSMS General | 磨辊监控系统 |
| G20 | HSLM General | 液压系统 |
| G30 | Classifier Oil Pump | 选粉机油泵 |
| G40 | High Pressure Pump | 高压油泵 |
| G50 | Hydraulic System | 液压抬辊/降辊 |
| G60 | Main Drive | 主电机驱动 |
| G65 | Water Injection | 磨辊喷水 |
| G71 | Grinding Aid | 助磨剂系统 |
| GC | Gas Circuit | 气体回路 |
| HGS | Hot Gas Supply | 热风供给 |
| MD | Mill Motor | 磨机电机 |
| RMF | Raw Material Feed | 原料喂料 |

### 2.2 标准功能块 (Standard Blocks)
- MOTOR: 标准电机控制块
- MOTOR_FC: 变频器电机控制块
- GROUP: 组控制块
- MEASUREMENT: 测量/限值监控块
- VALVE: 阀门控制块
- DAMPER: 风门控制块
- BAG_FILTER: 袋式过滤器控制块
- PID: PID调节块

## 3. 关键连锁关系

### 3.1 磨机启动连锁 (Mill Start Interlocks)
1. 辅助设备组运行 (AUX_RUN)
2. 齿轮箱润滑系统正常 (LQ01:RUN)
3. 液压系统 rollers raised (HS11:ARE_RAISED)
4. 选粉机运行 (SR1_C01_RN)
5. 密封风机运行 (FN1:RUN)
6. 磨机风机可用 (FN01:AVBL)
7. 无过程快速停止 (PQSTOP = FALSE)

### 3.2 磨机保护连锁 (Mill Protection Interlocks)
1. 主电机绕组温度 > H2
2. 主电机轴承温度 > H2
3. 齿轮箱润滑油流量低
4. 磨机壳体振动跳闸
5. 液压工作压力过低延迟

### 3.3 过程连锁 (Process Interlocks)
1. 磨机出口气体温度 > H2 → 快速停止
2. 磨机压差 > H2 → 快速停止
3. 磨机出口气体温度 < L2 → 报警
4. 风量 < L2 → 报警

## 4. 信号命名规则
- **N561_**: 设备编号前缀
- **N30_**: 选粉机系统 (30系列)
- **N40_**: 高压油泵系统 (40系列)
- **N561_50HT1_**: 液压系统 (50系列)
- **N561_RM1_**: 主驱动系统 (60系列)
- **N561_65_**: 喷水系统 (65系列)
- **N561_71_**: 助磨剂系统 (71系列)
- **1632_**: 新系统编号前缀
- **1662_**: 风机系统

## 5. 程序文件列表
1. `MainGroups.st` - 主程序组控制
2. `G30_Classifier.st` - 选粉机系统
3. `G40_HPP.st` - 高压油泵系统
4. `G50_Hydraulic.st` - 液压系统
5. `G60_MainDrive.st` - 主驱动系统
6. `G65_WaterInjection.st` - 喷水系统
7. `G71_GrindingAid.st` - 助磨剂系统
8. `Interlocks.st` - 连锁逻辑汇总
9. `ProcessLogic.st` - 过程控制逻辑
