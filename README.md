# Omni Memory

一个为 LLM 提供长期记忆能力的代理服务。兼容 OpenAI API 格式，可无缝接入任何支持 OpenAI API 的应用。

## 功能特性

- **多种记忆模式**
  - **内置模式 (builtin)**：模型在回复中自动添加记忆标签，代理自动解析并存储
  - **外接模型模式 (external)**：使用独立的模型定期总结对话生成记忆

- **多种注入方式**
  - **全量注入 (full)**：将所有记忆注入到系统提示词中
  - **RAG 注入 (rag)**：智能筛选与当前对话相关的记忆

- **记忆管理**
  - 支持添加、更新、删除记忆操作
  - 记忆带时间戳，便于追踪
  - 编号系统便于模型操作特定记忆

- **思维链模型支持**
  - 自动识别并保留 reasoning_content（思维链内容）
  - 只对最终输出进行记忆处理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/endpoints.json` 配置上游 API：

```json
[
  {
    "name": "your-provider",
    "url": "https://api.example.com/v1",
    "api_key": "your-api-key",
    "provider": "openai",
    "models": ["model-1", "model-2"],
    "enabled": true
  }
]
```

编辑 `config/memory_settings.json` 配置记忆模式：

```json
{
  "debug_mode": false,
  "memory_mode": "builtin",
  "injection_mode": "full",
  "summary_interval": 5,
  "rag_max_memories": 10
}
```

### 3. 启动服务

```bash
# Linux/Mac
./run.sh

# Windows
run.bat

# 或直接运行
python main.py
```

服务默认运行在 `http://localhost:8080`

### 4. 使用

将 OpenAI API 的 base_url 改为代理地址即可：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="any-key"  # 代理会使用配置的上游 API Key
)

response = client.chat.completions.create(
    model="qwen3-max",
    messages=[
        {"role": "user", "content": "你好，我叫小明"}
    ]
)
print(response.choices[0].message.content)
```

## 配置说明

### endpoints.json

| 字段 | 说明 |
|------|------|
| name | 端点名称（用于日志） |
| url | 上游 API 地址 |
| api_key | 上游 API 密钥 |
| provider | 提供商类型（openai/anthropic） |
| models | 支持的模型列表 |
| enabled | 是否启用 |

### memory_settings.json

| 字段 | 说明 | 默认值 |
|------|------|--------|
| debug_mode | 调试模式：开启后打印详细日志 | false |
| memory_mode | 记忆模式：builtin / external | builtin |
| injection_mode | 注入方式：full / rag | full |
| external_model_endpoint | 外接模型 API 地址 | - |
| external_model_api_key | 外接模型 API 密钥 | - |
| external_model_name | 外接模型名称 | - |
| summary_interval | 外接模式总结间隔（对话轮数） | 5 |
| rag_max_memories | RAG 模式最大记忆数 | 10 |

## 记忆模式详解

### 内置模式 (builtin)

模型在回复末尾添加记忆标签，代理自动解析：

```
你好小明！很高兴认识你！

<memory>
- [2026-02-28]用户姓名是小明
</memory>
```

**记忆操作格式**：

- **新增**：`- [日期]记忆内容`
- **更新**：`- [日期][UPDATE:编号]新内容`
- **删除**：`- [日期][DELETE:编号]`

### 外接模型模式 (external)

每隔 N 轮对话，使用独立模型总结对话并生成记忆操作。适用于不支持复杂指令的模型。

## API 接口

### OpenAI 兼容接口

- `POST /v1/chat/completions` - 聊天完成
- `GET /v1/models` - 获取模型列表

### 记忆管理接口

- `GET /memories` - 获取所有记忆
- `POST /memories` - 添加记忆
- `PUT /memories/{memory_id}` - 更新记忆
- `DELETE /memories/{memory_id}` - 删除记忆
- `GET /memories/search?keyword=xxx` - 搜索记忆

### Web 界面

访问 `http://localhost:8080/` 可使用 Web 管理界面查看和管理记忆。

## 数据存储

记忆数据存储在 `data/memories.json` 文件中，格式：

```json
[
  {
    "id": "mem_xxx",
    "content": "用户姓名是小明",
    "created_at": "2026-02-28T10:30:00",
    "updated_at": "2026-02-28T10:30:00",
    "source": "builtin_extraction"
  }
]
```

## 注意事项

1. **API Key 安全**：配置文件中的 API Key 请妥善保管，不要提交到版本控制
2. **记忆数量**：全量注入模式下，记忆过多会增加 token 消耗，建议定期清理
3. **思维链模型**：支持自动识别 reasoning_content，思维链中的记忆标签会被忽略

## 更多用途

[接入AstrBot](docs/ASTRBOT_GUIDE.md)

## 许可证

Apache License 2.0
