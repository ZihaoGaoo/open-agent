# open-agent

可配置的通用 Agent 平台。用户在平台上创建 agent，为其绑定**提示词 / MCP / Skill / Webhook** 等能力；创建后的 agent 可通过 **IM、API** 调用，并支持**多 agent 之间通信**。

- 后端：Python（FastAPI，async）
- 数据库：PostgreSQL
- 部署：单 Docker 镜像 + 外部 PostgreSQL

## 核心能力

- Agent 配置与管理（绑定模型、提示词、参数，挂载能力，配置可版本化）
- 可插拔能力：Prompt / MCP / Skill / Webhook
- 多模型支持（默认 Claude `claude-opus-4-8`，可切换 OpenAI 等）
- 多种调用：同步 REST、异步 run（轮询/回调）、SSE 流式
- IM 接入：Slack / Telegram / Discord
- 多 Agent 通信、会话与记忆、多租户与安全、可观测性

## 文档

- 总体架构设计：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 迭代路线图：[docs/ROADMAP.md](docs/ROADMAP.md)

> 当前处于**总体设计**阶段，已确定模块划分、技术栈与产品能力；各模块细化与代码实现按路线图迭代落地。
