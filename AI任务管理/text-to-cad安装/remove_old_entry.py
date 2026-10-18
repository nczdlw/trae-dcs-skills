# -*- coding: utf-8 -*-
"""尝试删除被安全中心规则拦截的旧文件名条目（带括号）。
删除失败不抛致命错，只报告结果，由主会话决定后续。"""
import os

OLD = r"D:\.AI\GITHUB\trae-dcs-skills\knowledge\70-工具与工作方法\text-to-cad(cadgen)安装配置说明_20261018.md"
print("存在:", os.path.exists(OLD))
try:
    os.remove(OLD)
    print("删除成功")
except Exception as e:
    print(f"删除失败: {e!r}")
