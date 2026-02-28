"""
记忆相关提示词定义
"""

from datetime import datetime


# ====== 内置记忆模式提示词 ======

BUILTIN_MEMORY_PROMPT = """\
# 记忆管理指南

你可以在对话中通过添加特定格式的XML标签来管理长期记忆。

## 何时记录记忆
- 用户分享的个人信息：生日、职业、兴趣爱好、性格特点
- 用户的偏好设置：喜欢的风格、语气、回复长度
- 重要事件：考试、旅行、纪念日、人生大事
- 长期目标：学习计划、职业规划、健身目标
- 人际关系：家人、朋友、宠物的信息

## 何时不记录记忆
- 临时性任务：帮忙写文章、翻译、计算
- 短期信息：明天的天气、今天的新闻
- 玩笑或虚构内容
- 未经证实的推测

## 如何记录记忆
在回复的最后，添加如下格式的记忆标签：

<memory>
- [YYYY-MM-DD]记忆内容1
- [YYYY-MM-DD]记忆内容2
</memory>

例如：
<memory>
- [2024-03-15]用户25岁，是一名软件工程师
- [2024-03-15]用户喜欢科幻小说和猫咪
</memory>

## 如何更新记忆
如果需要更新已有记忆，在记忆标签中使用 [UPDATE:记忆ID] 格式：

<memory>
- [2024-03-15][UPDATE:mem_123]用户26岁了，仍是一名软件工程师
</memory>

## 如何删除记忆
如果需要删除记忆，使用 [DELETE:记忆ID] 格式：

<memory>
- [2024-03-15][DELETE:mem_456]
</memory>

## 注意事项
- 每个<memory>标签可以包含多条记忆
- 记忆内容要简洁、客观
- 时间戳使用YYYY-MM-DD格式
- 如果本次对话没有新记忆需要记录，则不要添加<memory>标签
- 记忆标签不会被用户看到，系统会自动处理并移除
"""


# ====== 外接模型总结记忆提示词 ======

EXTERNAL_SUMMARY_PROMPT = """\
# 记忆总结任务

请根据提供的对话历史，总结需要长期记忆的信息。

## 需要记忆的信息
- 用户的个人资料：年龄、职业、居住地、性格
- 用户偏好：喜欢的主题、风格、语气、格式
- 重要事件：生日、纪念日、成就、变故
- 长期目标：学习计划、职业目标、生活目标
- 关系网络：家人、朋友、同事、宠物

## 不需要记忆的信息
- 临时问题或任务
- 短期安排（一周内）
- 日常闲聊
- 玩笑话
- AI生成的内容

## 输出格式
请严格按以下JSON格式输出：

```json
{
  "memories": [
    {
      "action": "add|update|delete",
      "id": "记忆ID(更新/删除时必需)",
      "content": "记忆内容(添加/更新时必需)"
    }
  ]
}
```

如果本次没有新记忆，返回：
```json
{"memories": []}
```

## 已有记忆
{existing_memories}

## 对话历史
{conversation}

请输出JSON格式的记忆操作：
"""


# ====== RAG注入提示词 ======

RAG_INJECTION_PROMPT = """\
# 记忆筛选任务

请根据当前对话内容，从提供的记忆中筛选出最相关的记忆。

## 筛选标准
- 与当前话题直接相关的记忆
- 有助于理解用户意图的记忆
- 可能影响回复风格的用户偏好

## 排除标准
- 与当前话题无关的旧记忆
- 可能产生干扰的不相关信息

## 输出格式
请严格按以下JSON格式输出：

```json
{
  "selected_memories": [
    "记忆ID1",
    "记忆ID2"
  ],
  "reason": "选择这些记忆的原因简要说明"
}
```

最多选择{max_memories}条最相关的记忆。

## 当前对话
{current_conversation}

## 可用记忆
{available_memories}

请输出JSON格式的筛选结果：
"""


# ====== 全量注入记忆格式化 ======

FULL_INJECTION_PROMPT_TEMPLATE = """\
# 长期记忆

以下是关于用户的历史记忆，请在回复时参考：

<memory>
{memories}
</memory>

请根据这些记忆，提供更加个性化和连贯的对话体验。
"""


# ====== 记忆操作解析提示词 ======

MEMORY_ACTION_PROMPT = """\
# 记忆操作识别

请分析对话内容，识别是否包含记忆操作。

## 当前对话
{conversation}

## 已有记忆
{existing_memories}

## 输出格式
请按以下JSON格式输出识别到的记忆操作：

```json
{
  "actions": [
    {
      "action": "add|update|delete",
      "id": "记忆ID(如已知)",
      "content": "新记忆内容",
      "reason": "操作原因"
    }
  ]
}
```
"""


def format_memories_for_injection(memories: list, mode: str = "full") -> str:
    """
    格式化记忆用于注入
    
    Args:
        memories: 记忆列表
        mode: 注入模式 (full 或 selected)
    
    Returns:
        格式化后的记忆字符串
    """
    if not memories:
        return ""
    
    lines = []
    for mem in memories:
        if isinstance(mem, dict):
            time_str = mem.get("created_at", "")[:10] if mem.get("created_at") else "未知"
            content = mem.get("content", "")
        else:
            time_str = mem.created_at[:10] if mem.created_at else "未知"
            content = mem.content
        
        lines.append(f"- [{time_str}]{content}")
    
    return "\n".join(lines)


def get_builtin_memory_instruction() -> str:
    """获取内置记忆模式指令"""
    return BUILTIN_MEMORY_PROMPT


def get_external_summary_prompt(conversation: str, existing_memories: str = "") -> str:
    """获取外接模型总结提示词"""
    return EXTERNAL_SUMMARY_PROMPT.format(
        conversation=conversation,
        existing_memories=existing_memories if existing_memories else "暂无"
    )


def get_rag_injection_prompt(current_conversation: str, available_memories: str, max_memories: int = 10) -> str:
    """获取RAG注入提示词"""
    return RAG_INJECTION_PROMPT.format(
        current_conversation=current_conversation,
        available_memories=available_memories,
        max_memories=max_memories
    )


def format_full_injection(memories_text: str) -> str:
    """格式化全量注入提示词"""
    return FULL_INJECTION_PROMPT_TEMPLATE.format(memories=memories_text)