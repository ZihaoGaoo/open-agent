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

## 本地快速开始

```bash
# 1. 准备环境
cp .env.example .env            # 按需填写；至少配置 DATABASE_URL
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"          # 需要 Python 3.12+

# 2. 建表（外部 PostgreSQL）
alembic upgrade head

# 3. 创建租户与 API Key（明文仅此一次可见）
python -m app.admin create-org --name "Acme"

# 4. 启动服务
uvicorn app.main:app --reload    # 或 ROLE=web/worker 用容器入口

# 5. 调用（同步）
curl -X POST localhost:8000/v1/agents \
  -H "X-API-Key: <上面的 key>" -H "Content-Type: application/json" \
  -d '{"name":"demo","system_prompt":"You are $role.","model":"claude-opus-4-8"}'

curl -X POST localhost:8000/v1/agents/<agent_id>/invoke \
  -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d '{"input":"你好","variables":{"role":"助手"}}'
```

> Docker：`docker compose up` 会以单镜像分别起 `web` / `worker` 两个进程 + 外部 PostgreSQL。

## 文档

- 总体架构设计：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 迭代路线图：[docs/ROADMAP.md](docs/ROADMAP.md)

> 进度：**M1 进行中** —— 应用骨架、核心数据表 + 迁移、API Key 鉴权、agent/prompt CRUD、
> 同步 `invoke` 闭环已就绪（默认 Claude Provider，多模型抽象层）。其余按路线图迭代。
