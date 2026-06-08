"""人格管理模块 - 支持 JSON / SQLite 双后端"""
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock


class PersonaStore(ABC):
    """存储后端抽象"""

    @abstractmethod
    def get_all(self) -> List[Dict]: ...

    @abstractmethod
    def get_by_id(self, pid: str) -> Optional[Dict]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Dict]: ...

    @abstractmethod
    def add(self, name: str, system_prompt: str = "",
            model: str = "", description: str = "") -> Dict: ...

    @abstractmethod
    def update(self, pid: str, **kwargs) -> Optional[Dict]: ...

    @abstractmethod
    def delete(self, pid: str) -> bool: ...

    @abstractmethod
    def get_active(self) -> Optional[Dict]: ...

    @abstractmethod
    def get_active_list(self) -> List[Dict]: ...

    @abstractmethod
    def set_active(self, pid: str) -> bool: ...


# ==================== JSON 后端 ====================

class JsonPersonaStore(PersonaStore):
    """JSON 文件存储（与原项目 config 风格一致）"""

    def __init__(self, data_dir: str = "./data"):
        self._path = Path(data_dir) / "personas.json"
        self._lock = Lock()
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._save([])

    def _load(self) -> List[Dict]:
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: List[Dict]):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Dict]:
        with self._lock:
            return self._load()

    def get_by_id(self, pid: str) -> Optional[Dict]:
        with self._lock:
            for p in self._load():
                if p["id"] == pid:
                    return p
        return None

    def get_by_name(self, name: str) -> Optional[Dict]:
        with self._lock:
            for p in self._load():
                if p["name"] == name:
                    return p
        return None

    def add(self, name: str, system_prompt: str = "",
            model: str = "", description: str = "") -> Dict:
        with self._lock:
            data = self._load()
            persona = {
                "id": str(uuid.uuid4()),
                "name": name,
                "system_prompt": system_prompt,
                "model": model,
                "description": description,
                "active": len(data) == 0,  # 第一个自动激活
                "created_at": datetime.now().isoformat(),
            }
            data.append(persona)
            self._save(data)
            return persona

    def update(self, pid: str, **kwargs) -> Optional[Dict]:
        allowed = {"name", "system_prompt", "model", "description"}
        with self._lock:
            data = self._load()
            for p in data:
                if p["id"] == pid:
                    for k, v in kwargs.items():
                        if k in allowed:
                            p[k] = v
                    self._save(data)
                    return p
        return None

    def delete(self, pid: str) -> bool:
        with self._lock:
            data = self._load()
            target = None
            for i, p in enumerate(data):
                if p["id"] == pid:
                    target = data.pop(i)
                    break
            if not target:
                return False
            # 删的是激活的 → 激活第一个
            if target["active"] and data:
                data[0]["active"] = True
            self._save(data)
            return True

    def get_active(self) -> Optional[Dict]:
        with self._lock:
            for p in self._load():
                if p["active"]:
                    return p
        return None

    def get_active_list(self) -> List[Dict]:
        with self._lock:
            return [p for p in self._load() if p["active"]]

    def set_active(self, pid: str) -> bool:
        """toggle 人格的 active 状态（不影响其他人格）"""
        with self._lock:
            data = self._load()
            found = False
            for p in data:
                if p["id"] == pid:
                    found = True
                    p["active"] = not p["active"]
                    break
            if found:
                self._save(data)
            return found


# ==================== SQLite 后端 ====================

class SqlitePersonaStore(PersonaStore):
    """SQLite 存储"""

    def __init__(self, data_dir: str = "./data"):
        self.db_path = Path(data_dir) / "omemo.db"
        self._lock = Lock()
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                system_prompt TEXT DEFAULT '',
                model TEXT DEFAULT '',
                description TEXT DEFAULT '',
                active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )""")

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _to_dict(self, row) -> Optional[Dict]:
        if not row:
            return None
        d = dict(row)
        d["active"] = bool(d["active"])
        return d

    # --- 下面直接搬你现有的方法，改 self._lock 就行 ---

    def get_all(self) -> List[Dict]:
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM personas ORDER BY created_at"
            ).fetchall()
            return [self._to_dict(r) for r in rows]

    def get_by_id(self, pid: str) -> Optional[Dict]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM personas WHERE id = ?", (pid,)
            ).fetchone()
            return self._to_dict(row)

    def get_by_name(self, name: str) -> Optional[Dict]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM personas WHERE name = ?", (name,)
            ).fetchone()
            return self._to_dict(row)

    def add(self, name: str, system_prompt: str = "",
            model: str = "", description: str = "") -> Dict:
        with self._lock, self._get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM personas"
            ).fetchone()[0]
            pid = str(uuid.uuid4())
            now = datetime.now().isoformat()
            active = 1 if count == 0 else 0
            conn.execute(
                "INSERT INTO personas VALUES (?,?,?,?,?,?,?)",
                (pid, name, system_prompt, model,
                 description, active, now)
            )
            return {
                "id": pid, "name": name,
                "system_prompt": system_prompt,
                "model": model, "description": description,
                "active": bool(active), "created_at": now
            }

    def update(self, pid: str, **kwargs) -> Optional[Dict]:
        allowed = {"name", "system_prompt", "model", "description"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_by_id(pid)
        sets = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [pid]
        with self._lock, self._get_conn() as conn:
            conn.execute(
                f"UPDATE personas SET {sets} WHERE id = ?", vals
            )
            row = conn.execute(
                "SELECT * FROM personas WHERE id = ?", (pid,)
            ).fetchone()
            return self._to_dict(row)

    def delete(self, pid: str) -> bool:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT active FROM personas WHERE id = ?", (pid,)
            ).fetchone()
            if not row:
                return False
            was_active = bool(row[0])
            conn.execute(
                "DELETE FROM personas WHERE id = ?", (pid,)
            )
            if was_active:
                first = conn.execute(
                    "SELECT id FROM personas ORDER BY created_at LIMIT 1"
                ).fetchone()
                if first:
                    conn.execute(
                        "UPDATE personas SET active = 1 WHERE id = ?",
                        (first[0],)
                    )
            return True

    def get_active(self) -> Optional[Dict]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM personas WHERE active = 1"
            ).fetchone()
            return self._to_dict(row)

    def get_active_list(self) -> List[Dict]:
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM personas WHERE active = 1 ORDER BY created_at"
            ).fetchall()
            return [self._to_dict(r) for r in rows]

    def set_active(self, pid: str) -> bool:
        """toggle 人格的 active 状态（不影响其他人格）"""
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT active FROM personas WHERE id = ?", (pid,)
            ).fetchone()
            if not row:
                return False
            new_val = 0 if row[0] else 1
            conn.execute(
                "UPDATE personas SET active = ? WHERE id = ?",
                (new_val, pid)
            )
            return True


# ==================== 工厂 ====================

def create_persona_store(backend: str = "json",
                         data_dir: str = "./data") -> PersonaStore:
    if backend == "sqlite":
        return SqlitePersonaStore(data_dir)
    return JsonPersonaStore(data_dir)
