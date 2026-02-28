"""
记忆存储模块
支持JSON文件存储
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from models import MemoryItem


class MemoryStorage:
    """记忆存储管理器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.memories_file = self.data_dir / "memories.json"
        self._lock = Lock()
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """确保数据文件存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.memories_file.exists():
            self._save_all([])
    
    def _load_all(self) -> List[Dict[str, Any]]:
        """加载所有记忆"""
        with self._lock:
            try:
                with open(self.memories_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
    
    def _save_all(self, memories: List[Dict[str, Any]]):
        """保存所有记忆"""
        with self._lock:
            with open(self.memories_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
    
    def get_all(self) -> List[MemoryItem]:
        """获取所有记忆"""
        data = self._load_all()
        return [MemoryItem(**item) for item in data]
    
    def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """根据ID获取记忆"""
        memories = self._load_all()
        for item in memories:
            if item.get("id") == memory_id:
                return MemoryItem(**item)
        return None
    
    def add(self, content: str, source: Optional[str] = None, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加新记忆"""
        now = datetime.now().isoformat()
        memory = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            created_at=now,
            updated_at=now,
            source=source,
            metadata=metadata or {}
        )
        
        memories = self._load_all()
        memories.append(memory.model_dump())
        self._save_all(memories)
        return memory
    
    def update(self, memory_id: str, content: str) -> Optional[MemoryItem]:
        """更新记忆内容"""
        memories = self._load_all()
        
        for i, item in enumerate(memories):
            if item.get("id") == memory_id:
                item["content"] = content
                item["updated_at"] = datetime.now().isoformat()
                memories[i] = item
                self._save_all(memories)
                return MemoryItem(**item)
        
        return None
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        memories = self._load_all()
        
        for i, item in enumerate(memories):
            if item.get("id") == memory_id:
                del memories[i]
                self._save_all(memories)
                return True
        
        return False
    
    def search(self, keyword: str) -> List[MemoryItem]:
        """搜索记忆"""
        memories = self._load_all()
        results = []
        
        keyword_lower = keyword.lower()
        for item in memories:
            content = item.get("content", "").lower()
            if keyword_lower in content:
                results.append(MemoryItem(**item))
        
        return results
    
    def clear(self):
        """清空所有记忆"""
        self._save_all([])
    
    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """获取最近添加的记忆"""
        memories = self._load_all()
        # 按创建时间排序，最新的在前
        sorted_memories = sorted(
            memories,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        return [MemoryItem(**item) for item in sorted_memories[:limit]]
    
    def batch_add(self, contents: List[str], source: Optional[str] = None) -> List[MemoryItem]:
        """批量添加记忆"""
        memories = self._load_all()
        new_memories = []
        now = datetime.now().isoformat()
        
        for content in contents:
            memory = {
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": now,
                "updated_at": now,
                "source": source,
                "metadata": {}
            }
            memories.append(memory)
            new_memories.append(MemoryItem(**memory))
        
        self._save_all(memories)
        return new_memories
    
    def batch_delete(self, memory_ids: List[str]) -> int:
        """批量删除记忆，返回删除数量"""
        memories = self._load_all()
        original_count = len(memories)
        
        memories = [item for item in memories if item.get("id") not in memory_ids]
        deleted_count = original_count - len(memories)
        
        self._save_all(memories)
        return deleted_count
    
    def count(self) -> int:
        """获取记忆总数"""
        return len(self._load_all())
    
    def export(self, file_path: str) -> bool:
        """导出记忆到文件"""
        try:
            memories = self._load_all()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出记忆失败: {e}")
            return False
    
    def import_(self, file_path: str, merge: bool = True) -> bool:
        """从文件导入记忆"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                new_memories = json.load(f)
            
            if not merge:
                self._save_all(new_memories)
            else:
                existing = self._load_all()
                existing_ids = {item.get("id") for item in existing}
                
                for item in new_memories:
                    if item.get("id") not in existing_ids:
                        existing.append(item)
                
                self._save_all(existing)
            
            return True
        except Exception as e:
            print(f"导入记忆失败: {e}")
            return False