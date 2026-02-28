"""
记忆总结器
用于外接模型总结记忆和RAG筛选
"""

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from memory.prompts import get_external_summary_prompt, get_rag_injection_prompt
from memory.manager import MemoryManager
from models import MemoryItem, MemoryActionItem, MemoryAction


class MemorySummarizer:
    """记忆总结器"""
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        model: str
    ):
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
    
    async def summarize_conversation(
        self,
        conversation: str,
        existing_memories: List[MemoryItem]
    ) -> List[MemoryActionItem]:
        """
        使用外接模型总结对话，生成记忆操作
        
        Args:
            conversation: 对话文本
            existing_memories: 已有记忆列表
        
        Returns:
            记忆操作列表
        """
        # 格式化已有记忆
        memories_text = json.dumps(
            [{"id": m.id, "content": m.content, "created_at": m.created_at} for m in existing_memories],
            ensure_ascii=False,
            indent=2
        )
        
        prompt = get_external_summary_prompt(conversation, memories_text)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专门用于分析和总结对话记忆的AI助手。请严格按照要求的JSON格式输出。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                return self._parse_memory_actions(content)
        
        except Exception as e:
            print(f"总结对话失败: {e}")
            return []
    
    async def select_relevant_memories(
        self,
        conversation: str,
        available_memories: List[MemoryItem],
        max_memories: int = 10
    ) -> List[MemoryItem]:
        """
        使用RAG模式筛选相关记忆
        
        Args:
            conversation: 当前对话
            available_memories: 可用记忆列表
            max_memories: 最多返回的记忆数量
        
        Returns:
            筛选后的记忆列表
        """
        if not available_memories:
            return []
        
        # 格式化可用记忆
        memories_text = json.dumps(
            [{"id": m.id, "content": m.content} for m in available_memories],
            ensure_ascii=False,
            indent=2
        )
        
        prompt = get_rag_injection_prompt(conversation, memories_text, max_memories)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专门用于筛选相关记忆的AI助手。请严格按照要求的JSON格式输出。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                selected_ids = self._parse_selected_memories(content)
                
                # 根据ID筛选记忆
                id_to_memory = {m.id: m for m in available_memories}
                selected = []
                for mid in selected_ids:
                    if mid in id_to_memory:
                        selected.append(id_to_memory[mid])
                
                return selected
        
        except Exception as e:
            print(f"筛选记忆失败: {e}")
            # 失败时返回所有记忆
            return available_memories[:max_memories]
    
    def _parse_memory_actions(self, content: str) -> List[MemoryActionItem]:
        """解析记忆操作JSON"""
        actions = []
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                # 尝试直接解析
                json_match = re.search(r'\{[\s\S]*"memories"[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)
            
            data = json.loads(content)
            
            if "memories" in data and isinstance(data["memories"], list):
                for item in data["memories"]:
                    action_type = item.get("action", "add")
                    
                    if action_type == "add":
                        actions.append(MemoryActionItem(
                            action=MemoryAction.ADD,
                            content=item.get("content", "")
                        ))
                    elif action_type == "update":
                        actions.append(MemoryActionItem(
                            action=MemoryAction.UPDATE,
                            id=item.get("id"),
                            content=item.get("content", "")
                        ))
                    elif action_type == "delete":
                        actions.append(MemoryActionItem(
                            action=MemoryAction.DELETE,
                            id=item.get("id")
                        ))
        
        except Exception as e:
            print(f"解析记忆操作失败: {e}")
        
        return actions
    
    def _parse_selected_memories(self, content: str) -> List[str]:
        """解析筛选的记忆ID"""
        selected_ids = []
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*"selected_memories"[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)
            
            data = json.loads(content)
            
            if "selected_memories" in data and isinstance(data["selected_memories"], list):
                selected_ids = data["selected_memories"]
        
        except Exception as e:
            print(f"解析筛选记忆失败: {e}")
        
        return selected_ids