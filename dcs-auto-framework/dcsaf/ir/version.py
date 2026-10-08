# -*- coding: utf-8 -*-
"""版本目录管理：每个版本一个子目录，记录版本说明与变更。"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class VersionManager:
    """IR 版本管理。

    目录结构：
    <base>/<version>/points.yaml 或 logic.yaml
    <base>/versions.json          # 版本清单
    """

    def __init__(self, base: str):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base / "versions.json"

    def _load_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        return {"versions": []}

    def _save_index(self, index: Dict[str, Any]) -> None:
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_versions(self) -> List[str]:
        return [v["version"] for v in self._load_index()["versions"]]

    def save(self, version: str, kind: str, data: Dict[str, Any], note: str = "") -> str:
        """保存一个 IR 版本。kind: points / logic。"""
        from .io import _dump  # 复用 io 的序列化

        index = self._load_index()
        if any(v["version"] == version for v in index["versions"]):
            raise ValueError(f"版本 '{version}' 已存在")

        ver_dir = self.base / version
        ver_dir.mkdir(parents=True, exist_ok=True)
        fname = "points.yaml" if kind == "points" else "logic.yaml"
        (ver_dir / fname).write_text(_dump(data, "yaml"), encoding="utf-8")

        index["versions"].append({
            "version": version,
            "kind": kind,
            "note": note,
            "created": datetime.now().isoformat(timespec="seconds"),
        })
        self._save_index(index)
        return str(ver_dir / fname)

    def load(self, version: str, kind: str) -> Dict[str, Any]:
        """加载指定版本的 IR 字典。"""
        import yaml

        ver_dir = self.base / version
        fname = "points.yaml" if kind == "points" else "logic.yaml"
        p = ver_dir / fname
        if not p.exists():
            raise FileNotFoundError(f"版本 '{version}' 的 {kind} 文件不存在")
        return yaml.safe_load(p.read_text(encoding="utf-8"))

    def promote(self, from_version: str, to_version: str, kind: str, note: str = "") -> str:
        """把某版本提升为新版本（复制内容）。"""
        data = self.load(from_version, kind)
        return self.save(to_version, kind, data, note)

    def rollback(self, to_version: str, kind: str) -> str:
        """回退到指定版本（用目标版本覆盖当前 latest 的 last 标记）。"""
        data = self.load(to_version, kind)
        return self.save(f"rollback_{to_version}", kind, data, f"回退自 {to_version}")
