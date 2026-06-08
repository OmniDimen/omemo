"""记忆存储模块 - SQLite，按人格隔离"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from models import MemoryItem

logger = logging.getLogger("omemo.storage")


class MemoryStorage:
    def __init__(self, data_dir: str = "./data"):
        self.db_path = Path(data_dir) / "omemo.db"
        self._lock = Lock()
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                persona_id TEXT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (persona_id)
                    REFERENCES personas(id) ON DELETE CASCADE
            )""")

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _to_item(self, row) -> MemoryItem:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return MemoryItem(**d)

    def get_all(self, persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE persona_id = ? ORDER BY created_at",
                    (persona_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at"
                ).fetchall()
            return [self._to_item(r) for r in rows]

    def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            return self._to_item(row) if row else None

    def add(self, content: str, persona_id: Optional[str] = None,
            source: Optional[str] = None,
            metadata: Optional[Dict] = None) -> MemoryItem:
        now = datetime.now().isoformat()
        mid = str(uuid.uuid4())
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT INTO memories VALUES (?,?,?,?,?,?,?)",
                (mid, persona_id, content, now, now, source, meta_str)
            )
        return MemoryItem(
            id=mid, persona_id=persona_id, content=content,
            created_at=now, updated_at=now,
            source=source, metadata=metadata or {}
        )

    def update(self, memory_id: str, content: str) -> Optional[MemoryItem]:
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE memories SET content = ?, updated_at = ? WHERE id = ?",
                (content, now, memory_id)
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            return self._to_item(row)

    def delete(self, memory_id: str) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
            return cur.rowcount > 0

    def search(self, keyword: str,
               persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE persona_id = ? AND content LIKE ?",
                    (persona_id, f"%{keyword}%")
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE content LIKE ?",
                    (f"%{keyword}%",)
                ).fetchall()
            return [self._to_item(r) for r in rows]

    def clear(self, persona_id: Optional[str] = None):
        with self._lock, self._get_conn() as conn:
            if persona_id:
                conn.execute(
                    "DELETE FROM memories WHERE persona_id = ?",
                    (persona_id,)
                )
            else:
                conn.execute("DELETE FROM memories")

    def get_recent(self, limit: int = 10,
                   persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE persona_id = ? ORDER BY created_at DESC LIMIT ?",
                    (persona_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [self._to_item(r) for r in rows]

    def batch_add(self, contents: List[str],
                  persona_id: Optional[str] = None,
                  source: Optional[str] = None) -> List[MemoryItem]:
        now = datetime.now().isoformat()
        items = []
        with self._lock, self._get_conn() as conn:
            for content in contents:
                mid = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO memories VALUES (?,?,?,?,?,?,?)",
                    (mid, persona_id, content, now, now, source, "{}")
                )
                items.append(MemoryItem(
                    id=mid, persona_id=persona_id, content=content,
                    created_at=now, updated_at=now,
                    source=source, metadata={}
                ))
        return items

    def batch_delete(self, memory_ids: List[str]) -> int:
        with self._lock, self._get_conn() as conn:
            total = 0
            for mid in memory_ids:
                cur = conn.execute(
                    "DELETE FROM memories WHERE id = ?", (mid,)
                )
                total += cur.rowcount
            return total

    def count(self, persona_id: Optional[str] = None) -> int:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE persona_id = ?",
                    (persona_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories"
                ).fetchone()
            return row[0]

    def count_by_persona(self) -> Dict[str, int]:
        """返回每个 persona_id 的记忆数量，key 为空字符串表示未绑定人格"""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT COALESCE(persona_id, '') as pid, COUNT(*) as cnt "
                "FROM memories GROUP BY persona_id"
            ).fetchall()
            return {row[0]: row[1] for row in rows}

    def export(self, file_path: str) -> bool:
        try:
            items = self.get_all()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([i.model_dump() for i in items],
                          f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("导出失败: %s", e)
            return False

    def import_(self, file_path: str, merge: bool = True,
                persona_id: Optional[str] = None) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not merge:
                self.clear(persona_id)
            with self._lock, self._get_conn() as conn:
                for item in data:
                    mid = item.get("id", str(uuid.uuid4()))
                    exists = conn.execute(
                        "SELECT id FROM memories WHERE id = ?",
                        (mid,)
                    ).fetchone()
                    if not exists:
                        now = datetime.now().isoformat()
                        conn.execute(
                            "INSERT INTO memories VALUES (?,?,?,?,?,?,?)",
                            (mid, persona_id, item["content"],
                             item.get("created_at", now),
                             item.get("updated_at", now),
                             item.get("source"),
                             json.dumps(item.get("metadata", {})))
                        )
            return True
        except Exception as e:
            logger.error("导入失败: %s", e)
            return False
