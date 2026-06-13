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
                metadata TEXT DEFAULT '{}'
            )""")
            # 多人格关联表
            conn.execute("""CREATE TABLE IF NOT EXISTS memory_personas (
                memory_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                PRIMARY KEY (memory_id, persona_id),
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )""")
            self._migrate_persona_ids(conn)

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _migrate_persona_ids(self, conn):
        """将旧的 persona_id 列数据迁移到 memory_personas 关联表"""
        # 检查 persona_id 列是否存在
        columns = [row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()]
        if "persona_id" not in columns:
            return
        # 迁移已有数据
        rows = conn.execute(
            "SELECT id, persona_id FROM memories WHERE persona_id IS NOT NULL AND persona_id != ''"
        ).fetchall()
        for row in rows:
            conn.execute(
                "INSERT OR IGNORE INTO memory_personas (memory_id, persona_id) VALUES (?, ?)",
                (row[0], row[1])
            )
        # 删除旧列（SQLite 不支持 DROP COLUMN < 3.35，用重建方式）
        # 先临时禁用外键检查，避免 DROP TABLE 被 memory_personas 的 FK 阻止
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories_new (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            INSERT INTO memories_new (id, content, created_at, updated_at, source, metadata)
            SELECT id, content, created_at, updated_at, source, metadata FROM memories
        """)
        conn.execute("DROP TABLE memories")
        conn.execute("ALTER TABLE memories_new RENAME TO memories")
        conn.execute("PRAGMA foreign_keys = ON")

    def _to_item(self, row, conn=None) -> MemoryItem:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        d["persona_ids"] = self._get_persona_ids(d["id"], conn)
        return MemoryItem(**d)

    def _get_persona_ids(self, memory_id: str, conn=None) -> List[str]:
        """获取记忆关联的人格ID列表"""
        if conn is None:
            with self._get_conn() as c:
                rows = c.execute(
                    "SELECT persona_id FROM memory_personas WHERE memory_id = ?",
                    (memory_id,)
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT persona_id FROM memory_personas WHERE memory_id = ?",
                (memory_id,)
            ).fetchall()
        return [row[0] for row in rows]

    def get_all(self, persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT DISTINCT m.* FROM memories m "
                    "JOIN memory_personas mp ON m.id = mp.memory_id "
                    "WHERE mp.persona_id = ? ORDER BY m.created_at",
                    (persona_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at"
                ).fetchall()
            return [self._to_item(r, conn) for r in rows]

    def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            return self._to_item(row, conn) if row else None

    def add(self, content: str, persona_ids: Optional[List[str]] = None,
            source: Optional[str] = None,
            metadata: Optional[Dict] = None) -> MemoryItem:
        now = datetime.now().isoformat()
        mid = str(uuid.uuid4())
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        persona_ids = persona_ids or []
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT INTO memories (id, content, created_at, updated_at, source, metadata) VALUES (?,?,?,?,?,?)",
                (mid, content, now, now, source, meta_str)
            )
            for pid in persona_ids:
                conn.execute(
                    "INSERT INTO memory_personas (memory_id, persona_id) VALUES (?, ?)",
                    (mid, pid)
                )
        return MemoryItem(
            id=mid, persona_ids=persona_ids, content=content,
            created_at=now, updated_at=now,
            source=source, metadata=metadata or {}
        )

    def update(self, memory_id: str, content: str,
               persona_ids: Optional[List[str]] = None) -> Optional[MemoryItem]:
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE memories SET content = ?, updated_at = ? WHERE id = ?",
                (content, now, memory_id)
            )
            if cur.rowcount == 0:
                return None
            # persona_ids is None means don't change; [] means clear; [...] means set
            if persona_ids is not None:
                conn.execute(
                    "DELETE FROM memory_personas WHERE memory_id = ?",
                    (memory_id,)
                )
                for pid in persona_ids:
                    conn.execute(
                        "INSERT INTO memory_personas (memory_id, persona_id) VALUES (?, ?)",
                        (memory_id, pid)
                    )
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            return self._to_item(row, conn)

    def delete(self, memory_id: str) -> bool:
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "DELETE FROM memory_personas WHERE memory_id = ?", (memory_id,)
            )
            cur = conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
            return cur.rowcount > 0

    def search(self, keyword: str,
               persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT DISTINCT m.* FROM memories m "
                    "JOIN memory_personas mp ON m.id = mp.memory_id "
                    "WHERE mp.persona_id = ? AND m.content LIKE ?",
                    (persona_id, f"%{keyword}%")
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE content LIKE ?",
                    (f"%{keyword}%",)
                ).fetchall()
            return [self._to_item(r, conn) for r in rows]

    def clear(self, persona_id: Optional[str] = None):
        with self._lock, self._get_conn() as conn:
            if persona_id:
                # 删除关联了该人格的记忆
                conn.execute(
                    "DELETE FROM memories WHERE id IN "
                    "(SELECT memory_id FROM memory_personas WHERE persona_id = ?)",
                    (persona_id,)
                )
            else:
                conn.execute("DELETE FROM memory_personas")
                conn.execute("DELETE FROM memories")

    def get_recent(self, limit: int = 10,
                   persona_id: Optional[str] = None) -> List[MemoryItem]:
        with self._lock, self._get_conn() as conn:
            if persona_id:
                rows = conn.execute(
                    "SELECT DISTINCT m.* FROM memories m "
                    "JOIN memory_personas mp ON m.id = mp.memory_id "
                    "WHERE mp.persona_id = ? ORDER BY m.created_at DESC LIMIT ?",
                    (persona_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [self._to_item(r, conn) for r in rows]

    def batch_add(self, contents: List[str],
                  persona_ids: Optional[List[str]] = None,
                  source: Optional[str] = None) -> List[MemoryItem]:
        now = datetime.now().isoformat()
        persona_ids = persona_ids or []
        items = []
        with self._lock, self._get_conn() as conn:
            for content in contents:
                mid = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO memories (id, content, created_at, updated_at, source, metadata) VALUES (?,?,?,?,?,?)",
                    (mid, content, now, now, source, "{}")
                )
                for pid in persona_ids:
                    conn.execute(
                        "INSERT INTO memory_personas (memory_id, persona_id) VALUES (?, ?)",
                        (mid, pid)
                    )
                items.append(MemoryItem(
                    id=mid, persona_ids=list(persona_ids), content=content,
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
                    "SELECT COUNT(DISTINCT m.id) FROM memories m "
                    "JOIN memory_personas mp ON m.id = mp.memory_id "
                    "WHERE mp.persona_id = ?",
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
            # 绑定了人格的记忆数（按 persona_id 分组）
            bound_rows = conn.execute(
                "SELECT mp.persona_id, COUNT(DISTINCT mp.memory_id) as cnt "
                "FROM memory_personas mp GROUP BY mp.persona_id"
            ).fetchall()
            result = {row[0]: row[1] for row in bound_rows}
            # 未绑定人格的记忆数
            unbound_row = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE id NOT IN (SELECT DISTINCT memory_id FROM memory_personas)"
            ).fetchone()
            result[""] = unbound_row[0]
            return result

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
                persona_ids: Optional[List[str]] = None) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not merge:
                self.clear()
            persona_ids = persona_ids or []
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
                            "INSERT INTO memories (id, content, created_at, updated_at, source, metadata) VALUES (?,?,?,?,?,?)",
                            (mid, item["content"],
                             item.get("created_at", now),
                             item.get("updated_at", now),
                             item.get("source"),
                             json.dumps(item.get("metadata", {})))
                        )
                        # 写入人格关联
                        item_pids = item.get("persona_ids", [])
                        if not item_pids and item.get("persona_id"):
                            item_pids = [item["persona_id"]]
                        if not item_pids:
                            item_pids = persona_ids
                        for pid in item_pids:
                            conn.execute(
                                "INSERT OR IGNORE INTO memory_personas (memory_id, persona_id) VALUES (?, ?)",
                                (mid, pid)
                            )
            return True
        except Exception as e:
            logger.error("导入失败: %s", e)
            return False
