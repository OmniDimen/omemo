"""
记忆相关提示词定义
"""

from datetime import datetime


# ====== 内置记忆模式提示词 ======

BUILTIN_MEMORY_PROMPT = """\
# 记忆管理指南

你可以在对话中通过添加特定格式的XML标签来管理长期记忆。

## 现有记忆编号说明
在「现有记忆」区域，如果存在现有记忆，那么每条记忆都有一个编号，格式为：
- 1.[日期]内容
- 2.[日期]内容
- 3.[日期]内容

编号1、2、3等对应每条现有记忆。你可以使用这些编号来更新或删除记忆。

## 何时记录新记忆
- 用户分享的全新个人信息：首次提到的名字、生日、职业、兴趣爱好
- 用户的偏好设置：喜欢的风格、语气、回复长度
- 重要事件：考试、旅行、纪念日、人生大事
- 长期目标：学习计划、职业规划、健身目标
- 人际关系：家人、朋友、宠物的信息
每个细节都需要独立设置一条记忆，比如叫什么名字，有什么兴趣爱好，都要拆开。

## 何时不记录记忆
- 临时性任务：帮忙写文章、翻译、计算
- 短期信息：明天的天气、今天的新闻
- 玩笑或虚构内容
- 未经证实的推测
- **已有记录的信息**：如果已有"用户姓名是小明"，不要重复记录

## 何时更新记忆而非新增
当用户提供的信息是对现有记忆的**修改或补充**时，应使用UPDATE，比如：
- 改名：用户说"我不叫小明了，叫我小张" → [UPDATE:对应编号]用户姓名是小张
- 年龄增长：用户说"我今年26岁了"（现有记录是25岁）→ [UPDATE:对应编号]用户26岁

## 何时删除记忆
- 信息已过时且无保留价值
- 用户明确要求忘记某事
- 记忆内容有误且无需保留

## 操作格式

在响应底部添加下面的内容完成记忆的添加或者删改：

### 新增记忆
<memory>
- [YYYY-MM-DD]记忆内容
</memory>

### 更新记忆（使用编号）
<memory>
- [2024-03-15][UPDATE:1]用户姓名是小张
</memory>

### 删除记忆（使用编号）
<memory>
- [2024-03-15][DELETE:2]
</memory>

### 混合操作
<memory>
- [2024-03-15][UPDATE:1]用户姓名是小张
- [2024-03-15]用户最近在学习Python
</memory>

## 重要提醒
- 每条记忆只记录一个独立的事实
- 编号必须对应现有记忆中的编号，不要编造编号
- 不要重复记录已有信息
- 如果本次没有记忆操作，不要添加<memory>标签
- 记忆标签不会被用户看到
"""


# ====== 外接模型总结记忆提示词 ======

EXTERNAL_SUMMARY_PROMPT = """\
# 记忆总结任务

请根据提供的对话历史，分析并管理长期记忆。

## 需要记忆的信息
- 用户的个人资料：姓名、年龄、职业、居住地、性格
- 用户偏好：喜欢的主题、风格、语气、格式
- 重要事件：生日、纪念日、成就、变故
- 长期目标：学习计划、职业目标、生活目标
- 关系网络：家人、朋友、同事、宠物

每个独立的事实应该是一条独立的记忆。

## 不需要记忆的信息
- 临时问题或任务
- 短期安排（一周内）
- 日常闲聊
- 玩笑话
- AI生成的内容
- **已有记录的信息**：如果已有记忆中包含某信息，不要重复添加

## 何时更新而非新增
当用户提供的信息是对已有记忆的**修改**时，使用 update：
- 改名：已有"用户姓名是小明"，用户说"我叫小张" → update 那条记忆
- 年龄变化：已有"用户25岁"，用户说"我今年26了" → update 那条记忆
- 信息更正：已有"用户是工程师"，用户说"我其实是设计师" → update 那条记忆

## 何时删除记忆
- 信息已过时且无保留价值
- 用户明确要求忘记某事

## 输出格式
请严格按以下JSON格式输出：

```json
{{
  "memories": [
    {{
      "action": "add",
      "content": "记忆内容"
    }},
    {{
      "action": "update",
      "id": "已有记忆的ID",
      "content": "新的记忆内容"
    }},
    {{
      "action": "delete",
      "id": "要删除的记忆ID"
    }}
  ]
}}
```

**重要**：
- add 操作不需要 id
- update 和 delete 操作必须使用「已有记忆」中对应的 id

如果本次没有记忆操作，返回：
```json
{{"memories": []}}
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
{{
  "selected_memories": [
    "记忆ID1",
    "记忆ID2"
  ],
  "reason": "选择这些记忆的原因简要说明"
}}
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
{{
  "actions": [
    {{
      "action": "add|update|delete",
      "id": "记忆ID(如已知)",
      "content": "新记忆内容",
      "reason": "操作原因"
    }}
  ]
}}
```
"""


def format_memories_for_injection(memories: list, mode: str = "full") -> str:
    """
    格式化记忆用于注入（带编号）
    
    Args:
        memories: 记忆列表
        mode: 注入模式 (full 或 selected)
    
    Returns:
        格式化后的记忆字符串
    """
    if not memories:
        return ""
    
    lines = []
    for idx, mem in enumerate(memories, start=1):
        if isinstance(mem, dict):
            time_str = mem.get("created_at", "")[:10] if mem.get("created_at") else "未知"
            content = mem.get("content", "")
            mem_id = mem.get("id", str(idx))
        else:
            time_str = mem.created_at[:10] if mem.created_at else "未知"
            content = mem.content
            mem_id = mem.id if mem.id else str(idx)
        
        # 格式: - 编号.[日期]内容
        lines.append(f"- {idx}.[{time_str}]{content}")
    
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
