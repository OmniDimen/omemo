"""人格管理模块"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock


class PersonaManager:
    def __init__(self, data_dir: str = "./data"):
        self.file = Path(data_dir) / "personas.json"
        self._lock = Lock()
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        if not self.file.exists():
            self._save([])

    def _load(self) -> List[Dict]:
        with self._lock:
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []

    def _save(self, data: List[Dict]):
        with self._lock:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Dict]:
        return self._load()

    def get_by_id(self, pid: str) -> Optional[Dict]:
        for p in self._load():
            if p["id"] == pid:
                return p
        return None

    def add(self, name: str, system_prompt: str = "",
            model: str = "", description: str = "") -> Dict:
        data = self._load()
        persona = {
            "id": str(uuid.uuid4()),
            "name": name,
            "system_prompt": system_prompt,
            "model": model,
            "description": description,
            "active": len(data) == 0,
            "created_at": datetime.now().isoformat()
        }
        data.append(persona)
        self._save(data)
        return persona

    def update(self, pid: str, **kwargs) -> Optional[Dict]:
        data = self._load()
        for i, p in enumerate(data):
            if p["id"] == pid:
                for k, v in kwargs.items():
                    if k in p and k not in ("id", "created_at"):
                        p[k] = v
                data[i] = p
                self._save(data)
                return p
        return None

    def delete(self, pid: str) -> bool:
        data = self._load()
        for i, p in enumerate(data):
            if p["id"] == pid:
                was_active = p.get("active", False)
                del data[i]
                if was_active and data:
                    data[0]["active"] = True
                self._save(data)
                return True
        return False

    def get_active(self) -> Optional[Dict]:
        for p in self._load():
            if p.get("active"):
                return p
        return None

    def set_active(self, pid: str) -> bool:
        data = self._load()
        found = False
        for p in data:
            p["active"] = (p["id"] == pid)
            if p["id"] == pid:
                found = True
        if found:
            self._save(data)
        return found
