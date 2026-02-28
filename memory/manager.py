"""
记忆管理器
负责记忆的CRUD操作和注入逻辑
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from memory.storage import MemoryStorage
from memory.prompts import (
    format_memories_for_injection,
    format_full_injection,
    get_rag_injection_prompt
)
from models import MemoryItem, MemoryAction, MemoryActionItem, ChatMessage
from config import MemorySettings, debug_print


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, storage: MemoryStorage, settings: MemorySettings):
        self.storage = storage
        self.settings = settings
        self.conversation_counter = 0
        self.pending_summaries: List[ChatMessage] = []
        self.current_index_to_id: Dict[int, str] = {}  # 编号到记忆ID的映射
    
    def get_all_memories(self) -> List[MemoryItem]:
        """获取所有记忆"""
        return self.storage.get_all()
    
    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """根据ID获取记忆"""
        return self.storage.get_by_id(memory_id)
    
    def add_memory(self, content: str, source: str = "manual") -> MemoryItem:
        """手动添加记忆"""
        return self.storage.add(content=content, source=source)
    
    def update_memory(self, memory_id: str, content: str) -> Optional[MemoryItem]:
        """更新记忆"""
        return self.storage.update(memory_id=memory_id, content=content)
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.storage.delete(memory_id=memory_id)
    
    def search_memories(self, keyword: str) -> List[MemoryItem]:
        """搜索记忆"""
        return self.storage.search(keyword)
    
    def format_memories_for_system(self, memories: List[MemoryItem]) -> Tuple[str, Dict[int, str]]:
        """
        格式化记忆为系统提示词格式（带编号）
        
        Returns:
            (格式化后的字符串, 编号到ID的映射)
        """
        if not memories:
            return "", {}
        
        lines = []
        index_to_id = {}
        
        for idx, mem in enumerate(memories, start=1):
            # 只显示日期: YYYY-MM-DD
            time_str = mem.created_at[:10] if mem.created_at and len(mem.created_at) >= 10 else "未知"
            lines.append(f"- {idx}.[{time_str}]{mem.content}")
            index_to_id[idx] = mem.id
        
        return "\n".join(lines), index_to_id
    
    def build_system_prompt_with_memories(
        self,
        original_system: Optional[str],
        memories: List[MemoryItem],
        mode: str = "full"
    ) -> str:
        """
        构建带记忆的系统提示词
        
        Args:
            original_system: 原始系统提示词
            memories: 记忆列表
            mode: 注入模式 (full 或 selected)
        
        Returns:
            完整的系统提示词
        """
        from datetime import datetime
        
        parts = []
        
        # 注入当前时间（精确到分钟）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        parts.append(f"[当前时间: {current_time}]")
        
        # 添加原始系统提示词
        if original_system:
            parts.append(original_system)
        
        # 添加记忆
        if memories:
            memories_text, index_to_id = self.format_memories_for_system(memories)
            memory_section = format_full_injection(memories_text)
            parts.append(memory_section)
        
        return "\n\n".join(parts)
    
    def build_builtin_system_prompt(
        self,
        original_system: Optional[str],
        memories: List[MemoryItem]
    ) -> str:
        """
        构建内置记忆模式的系统提示词
        包含记忆操作指导
        """
        from memory.prompts import get_builtin_memory_instruction
        from datetime import datetime
        
        parts = []
        
        # 注入当前时间（精确到分钟）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        parts.append(f"[当前时间: {current_time}]")
        
        if original_system:
            parts.append(original_system)
        
        # 添加记忆操作指导
        parts.append(get_builtin_memory_instruction())
        
        # 添加现有记忆
        if memories:
            memories_text, index_to_id = self.format_memories_for_system(memories)
            # 存储编号到ID的映射，供后续解析使用
            self.current_index_to_id = index_to_id
            parts.append(f"## 现有记忆\n\n<memory>\n{memories_text}\n</memory>")
        else:
            self.current_index_to_id = {}
        
        return "\n\n".join(parts)
    
    def extract_memory_operations_from_response(self, response_text: str) -> Tuple[str, List[MemoryActionItem]]:
        """
        从模型响应中提取记忆操作
        
        Returns:
            (清理后的响应, 记忆操作列表)
        """
        debug_print(f"[记忆提取] 原始响应长度: {len(response_text)}")
        debug_print(f"[记忆提取] 原始响应结尾: {repr(response_text[-200:])}")
        
        # 首先检查原始响应中是否有完整的 <memory>...</memory> 标签对
        # 只有在确保标签完整且不在思维链内时才提取
        
        # 步骤1: 找出所有思维链区域，记录它们的起始和结束位置
        thinking_regions = []
        thinking_patterns = [
            (r'<thinking>.*?</thinking>', re.DOTALL),
            (r'<think>.*?</think>', re.DOTALL),
            (r'<reasoning>.*?</reasoning>', re.DOTALL),
        ]
        
        for pattern, flags in thinking_patterns:
            for match in re.finditer(pattern, response_text, flags):
                thinking_regions.append((match.start(), match.end()))
        
        # 步骤2: 找出所有 <memory>...</memory> 标签
        memory_pattern = r'<memory>\s*(.*?)\s*</memory>'
        memory_matches = list(re.finditer(memory_pattern, response_text, re.DOTALL))
        
        if not memory_matches:
            debug_print("[记忆提取] 未找到完整的<memory>标签对")
            return response_text, []
        
        debug_print(f"[记忆提取] 找到 {len(memory_matches)} 个<memory>标签")
        
        # 步骤3: 找出不在思维链内的 memory 标签
        valid_memory_matches = []
        for match in memory_matches:
            match_start, match_end = match.start(), match.end()
            # 检查这个 match 是否在任何思维链区域内
            in_thinking = any(start <= match_start < end for start, end in thinking_regions)
            if not in_thinking:
                valid_memory_matches.append(match)
                debug_print(f"[记忆提取] 发现有效<memory>标签在位置 {match_start}-{match_end}")
            else:
                debug_print(f"[记忆提取] 忽略思维链内的<memory>标签在位置 {match_start}-{match_end}")
        
        if not valid_memory_matches:
            debug_print("[记忆提取] 所有<memory>标签都在思维链内，忽略")
            return response_text, []
        
        # 步骤4: 解析记忆内容（只处理第一个有效的 memory 标签）
        memory_match = valid_memory_matches[0]
        memory_content = memory_match.group(1).strip()
        debug_print(f"[记忆提取] 提取记忆内容: {repr(memory_content[:200])}")
        
        # 解析记忆条目
        actions = []
        
        # 尝试按行分割
        if '\n' in memory_content:
            lines = memory_content.split('\n')
        else:
            lines = [memory_content]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 确保行以 - 开头
            if not line.startswith('-'):
                dash_idx = line.find('- ')
                if dash_idx >= 0:
                    line = line[dash_idx:]
                else:
                    continue
            
            # 检查是否是删除操作
            # 支持两种格式：[DELETE:1] 或 [DELETE:mem_xxx]
            delete_match = re.search(r'\[DELETE:([^\]]+)\]', line)
            if delete_match:
                memory_ref = delete_match.group(1).strip()
                # 如果是数字编号，转换为实际ID
                if memory_ref.isdigit():
                    memory_id = self.current_index_to_id.get(int(memory_ref), memory_ref)
                else:
                    memory_id = memory_ref
                actions.append(MemoryActionItem(
                    action=MemoryAction.DELETE,
                    id=memory_id
                ))
                debug_print(f"[记忆提取] 删除记忆: {memory_ref} -> {memory_id}")
                continue
            
            # 检查是否是更新操作
            # 支持两种格式：[UPDATE:1]内容 或 [UPDATE:mem_xxx]内容
            update_match = re.search(r'\[UPDATE:([^\]]+)\]', line)
            if update_match:
                memory_ref = update_match.group(1).strip()
                # 如果是数字编号，转换为实际ID
                if memory_ref.isdigit():
                    memory_id = self.current_index_to_id.get(int(memory_ref), memory_ref)
                else:
                    memory_id = memory_ref
                    
                # 提取内容部分（UPDATE标签之后的内容）
                # 格式: - [日期][UPDATE:1]内容 或 - [UPDATE:1][日期]内容
                after_update = line[update_match.end():].strip()
                
                # 尝试提取日期后的内容
                date_match = re.search(r'\[\d{4}-\d{2}-\d{2}\]\s*(.+)', after_update)
                if date_match:
                    content_part = date_match.group(1).strip()
                else:
                    content_part = after_update
                
                if content_part:
                    actions.append(MemoryActionItem(
                        action=MemoryAction.UPDATE,
                        id=memory_id,
                        content=content_part
                    ))
                    debug_print(f"[记忆提取] 更新记忆: {memory_ref} -> {memory_id}, 内容: {content_part}")
                continue
            
            # 添加操作
            # 支持格式: - [日期]内容 或 - 编号.[日期]内容
            # 如果有编号说明是现有记忆，跳过
            add_match = re.search(r'-\s*(\d+)\.\s*\[\d{4}-\d{2}-\d{2}\]\s*(.+)', line)
            if add_match:
                # 有编号的是现有记忆，不是新增操作，跳过
                debug_print(f"[记忆提取] 跳过现有记忆: {line[:50]}")
                continue
            
            # 真正的添加操作
            content_match = re.search(r'\[\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?\]\s*(.+)', line)
            if content_match:
                content = content_match.group(1).strip()
                if content:
                    actions.append(MemoryActionItem(
                        action=MemoryAction.ADD,
                        content=content
                    ))
                    debug_print(f"[记忆提取] 添加记忆: {content}")
        
        # 步骤5: 移除所有有效的 memory 标签（从后往前移除，避免位置变化）
        cleaned_response = response_text
        for match in reversed(valid_memory_matches):
            start, end = match.start(), match.end()
            # 移除标签及其周围的可能换行
            # 往前看是否有换行，往后看是否有换行
            while start > 0 and cleaned_response[start-1] in '\n\r':
                start -= 1
            while end < len(cleaned_response) and cleaned_response[end] in '\n\r':
                end += 1
            cleaned_response = cleaned_response[:start] + cleaned_response[end:]
        
        cleaned_response = cleaned_response.strip()
        debug_print(f"[记忆提取] 清理后响应长度: {len(cleaned_response)}")
        debug_print(f"[记忆提取] 清理后响应结尾: {repr(cleaned_response[-100:])}")
        
        return cleaned_response, actions
    
    def apply_memory_actions(self, actions: List[MemoryActionItem]) -> Dict[str, Any]:
        """
        应用记忆操作
        
        Returns:
            操作结果统计
        """
        results = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "errors": []
        }
        
        for action in actions:
            try:
                if action.action == MemoryAction.ADD:
                    self.storage.add(
                        content=action.content,
                        source="builtin_extraction"
                    )
                    results["added"] += 1
                
                elif action.action == MemoryAction.UPDATE:
                    if action.id and action.content:
                        if self.storage.update(action.id, action.content):
                            results["updated"] += 1
                        else:
                            results["errors"].append(f"更新失败: ID {action.id} 不存在")
                
                elif action.action == MemoryAction.DELETE:
                    if action.id:
                        if self.storage.delete(action.id):
                            results["deleted"] += 1
                        else:
                            results["errors"].append(f"删除失败: ID {action.id} 不存在")
            
            except Exception as e:
                results["errors"].append(f"操作失败: {e}")
        
        return results
    
    def prepare_messages_with_memories(
        self,
        messages: List[ChatMessage],
        injection_mode: str,
        memories: Optional[List[MemoryItem]] = None
    ) -> List[ChatMessage]:
        """
        准备消息列表，注入记忆
        
        Args:
            messages: 原始消息列表
            injection_mode: 注入模式 (full 或 rag)
            memories: 预选的记忆(RAG模式使用)
        
        Returns:
            处理后的消息列表
        """
        if not messages:
            return messages
        
        # 找到系统消息或创建新的
        system_msg_idx = -1
        for i, msg in enumerate(messages):
            if msg.role == "system":
                system_msg_idx = i
                break
        
        original_system = None
        if system_msg_idx >= 0:
            original_system = messages[system_msg_idx].content
        
        # 准备要注入的记忆
        if memories is None:
            memories = self.get_all_memories()
        
        # 构建新的系统提示词
        if self.settings.memory_mode == "builtin":
            new_system = self.build_builtin_system_prompt(original_system, memories)
        else:
            new_system = self.build_system_prompt_with_memories(original_system, memories, injection_mode)
        
        # 更新或添加系统消息
        result_messages = list(messages)
        if system_msg_idx >= 0:
            result_messages[system_msg_idx] = ChatMessage(role="system", content=new_system)
        else:
            result_messages.insert(0, ChatMessage(role="system", content=new_system))
        
        return result_messages
    
    def get_conversation_text(self, messages: List[ChatMessage], last_n: int = 4) -> str:
        """获取最近n轮对话的文本"""
        recent_messages = messages[-last_n:] if len(messages) > last_n else messages
        lines = []
        for msg in recent_messages:
            role_name = "User" if msg.role == "user" else "Assistant" if msg.role == "assistant" else "System"
            lines.append(f"{role_name}: {msg.content}")
        return "\n".join(lines)
