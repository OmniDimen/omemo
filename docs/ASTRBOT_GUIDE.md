# 🤖 Omni Memory × AstrBot 快速接入指南

Author: [Omnitopia](https://github.com/Omnitopia)

> 让你的 AstrBot 机器人拥有长期记忆能力

---

## 前提条件

- AstrBot 已正常运行（本地或 Docker 部署均可）
- Omni Memory 已启动并配置好上游模型端点（参见 QUICKSTART.md）
- 你的 LLM 已在 LM Studio / Ollama / 云端 API 中正常运行

## 架构说明

接入后的请求链路：

```
QQ 用户发消息 → AstrBot → Omni Memory → LLM
                              ↕
                        memories.json（自动记忆）
```

AstrBot 不再直连 LLM，而是通过 Omni Memory 中转，记忆的注入和提取全部自动完成。

---

## 第一步：确认你的部署情况

根据你的环境，AstrBot 连接 Omni Memory 的地址有所不同。请对号入座：

### 情况 A：AstrBot 和 Omni Memory 都在本地直接运行

最简单的情况，地址就是 localhost。

```
AstrBot 填写的 API Base URL：http://localhost:8080/v1
```

### 情况 B：AstrBot 在 Docker 中运行，Omni Memory 在宿主机运行

Docker 容器内的 localhost 指向容器自身，不是宿主机。需要使用宿主机的局域网 IP。

先在宿主机上查询 IP：
- Mac：系统偏好设置 → 网络，或终端输入 `ifconfig | grep "inet "`
- Linux：终端输入 `hostname -I`

```
AstrBot 填写的 API Base URL：http://192.168.x.x:8080/v1
```

> 将 `192.168.x.x` 替换为你实际查到的 IP 地址

### 情况 C：AstrBot 使用云端 API（如 OpenAI / Anthropic / DeepSeek / 硅基流动等）

如果你原本就是用的云端 API，只需要把 API 地址从云端改为 Omni Memory 的地址，然后在 Omni Memory 的 Web UI 中配置云端 API 作为上游端点即可。

```
原来 AstrBot 填的：https://api.example.com/v1
改为 Omni Memory：http://localhost:8080/v1（或对应 IP）
```

然后在 Omni Memory Web UI → 添加端点：
- URL 填原来的云端地址（如 `https://api.example.com/v1`）
- API Key 填你的云端密钥
- 模型名填你使用的模型

> 如果你自定义了 Omni Memory 端口（通过 .env 的 PORT 字段），请将上述地址中的 8080 替换为你实际使用的端口

---

## 第二步：修改 AstrBot 的 LLM 配置

进入 AstrBot 管理后台，找到你的 LLM 提供商配置（通常在"模型提供商"或"Provider"设置中）：

1. 将 **API Base URL** 改为第一步确认的 Omni Memory 地址
2. **API Key** 保持不变（Omni Memory 会原样转发给上游）
3. **模型名称** 必须与 Omni Memory 端点配置中的模型名一致

> ⚠️ 注意：URL 末尾不要有多余空格，否则会导致 404 错误

---

## 第三步：测试

在 QQ 上给机器人发一条包含个人信息的消息，例如：

```
你好，我叫小明，我是一名程序员
```

然后打开 Omni Memory 的 Web UI（默认 http://localhost:8080），进入「记忆管理」页面，检查是否自动生成了类似这样的记忆：

```
用户名叫小明
用户是一名程序员
```

如果看到了，说明接入成功 🎉

---

## 已知限制

**单用户记忆**：当前版本的 Omni Memory 所有对话共享一个 memories.json，这意味着不同 QQ 用户与机器人的对话记忆会混在一起。如果你的机器人会和多个用户聊天，需要注意这一点。

**多模态兼容性**：AstrBot 默认使用 OpenAI 多模态消息格式（content 为列表而非字符串），需要确保 Omni Memory 已应用相关兼容性补丁（参见项目 README 或联系维护者）。

---

## 常见问题

**Q: 报 404 Not Found**
A: 检查 AstrBot 填写的 API URL 末尾是否有多余空格，正确格式是 `http://x.x.x.x:8080/v1`

**Q: 报 400 validation errors**
A: 旧版本不支持 AstrBot 的多模态消息格式，该问题已在当前版本修复。如仍遇到，请确认使用的是最新版本

**Q: 报 "failed to process image"**
A: 对话历史中可能包含旧的图片数据（如 Playwright 截图等）导致上游模型报错，尝试在 AstrBot 中清空该模型的对话历史后重试

**Q: Docker 中 AstrBot 连不上 Omni Memory**
A: Docker 容器内的 localhost 指向容器自身，需要使用宿主机的局域网 IP 地址
