from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from cli_anything.joplin.core import project as project_mod


@dataclass
class Session:
    project: Optional[dict] = None
    project_path: Optional[str] = None
    _modified: bool = False
    _undo_stack: list[dict] = field(default_factory=list)
    _redo_stack: list[dict] = field(default_factory=list)

    def has_project(self) -> bool:
        return self.project is not None

    def set_project(self, project: dict, path: Optional[str] = None) -> None:
        self.project = project
        self.project_path = path
        self._modified = False
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_project(self) -> dict:
        if not self.project:
            raise RuntimeError("No project loaded")
        return self.project

    def snapshot(self, reason: str) -> None:
        if not self.project:
            raise RuntimeError("No project loaded")
        self._undo_stack.append(copy.deepcopy(self.project))
        self._redo_stack.clear()
        self._modified = True
        project_mod.add_history(self.project, "snapshot", {"reason": reason})

    def undo(self) -> dict:
        if not self._undo_stack:
            raise RuntimeError("Nothing to undo")
        if self.project:
            self._redo_stack.append(copy.deepcopy(self.project))
        self.project = self._undo_stack.pop()
        self._modified = True
        return self.project

    def redo(self) -> dict:
        if not self._redo_stack:
            raise RuntimeError("Nothing to redo")
        if self.project:
            self._undo_stack.append(copy.deepcopy(self.project))
        self.project = self._redo_stack.pop()
        self._modified = True
        return self.project

    def status(self) -> dict:
        return {
            "has_project": self.has_project(),
            "project_path": self.project_path,
            "modified": self._modified,
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
        }

    def _locked_save_json(self, path: str, data: dict) -> None:
        lock_path = f"{path}.lock"
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        finally:
            os.close(lock_fd)

    def save_session(self, path: Optional[str] = None) -> str:
        if not self.project:
            raise RuntimeError("No project loaded")
        target = path or self.project_path
        if not target:
            raise RuntimeError("No project path set")
        self.project["updated_at"] = project_mod.utc_now()
        self._locked_save_json(target, self.project)
        self.project_path = target
        self._modified = False
        return target
