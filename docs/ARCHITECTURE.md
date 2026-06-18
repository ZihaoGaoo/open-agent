# open-agent · 总体架构设计

> 可配置的通用 Agent 平台。用户在平台上创建 agent，绑定提示词、MCP、Skill、Webhook 等能力；创建后的 agent 可通过 IM、API 调用，并支持多 agent 之间通信。后端 Python，数据库 PostgreSQL，整体打包为 Docker 部署。
>
> 本文档为**总体设计**，确定模块划分、技术栈、产品能力、数据模型与目录骨架。各模块细化与代码实现见 [ROADMAP](./ROADMAP.md) 的后续迭代。

## 1. 关键选型

| 维度 | 决策 |
|---|---|
| 核心引擎 | **多模型抽象层**，Claude（`claude-opus-4-8`）为默认/参考 Provider，OpenAI 等可插拔 |
| IM 渠道 | 优先 **Slack / Telegram / Discord** |
| 打包 | **单镜像应用 + 外部 PostgreSQL**（PG 不塞进应用镜像） |
| 调用模式 | **同步 + 异步都要**：同步 REST、异步 run（轮询/回调）、SSE 流式 |

---

## 2. 产品主要能力

1. **Agent 配置与管理**：在控制台/API 创建 agent，绑定模型、提示词、参数（effort / max_tokens 等），挂载能力（MCP / Skill / Webhook）。配置可版本化、可回滚。
2. **能力绑定（可插拔）**
   - **Prompt**：系统提示词模板 + 变量插值。
   - **MCP**：连接 MCP server（stdio / HTTP），自动发现并调用其工具。
   - **Skill**：基于文件系统的 Skill（`SKILL.md`），按需渐进加载。
   - **Webhook**：把外部 HTTP 接口声明为可调用工具（入参 JSON Schema、鉴权、响应映射）。
3. **多模型支持**：统一 Provider 接口，默认 Claude，可切换 OpenAI 等。
4. **多种调用方式**：同步调用、异步任务（run + 轮询/回调）、SSE 流式输出。
5. **IM 接入**：Slack / Telegram / Discord 双向接入（入站 webhook、出站回复、身份映射、会话续接）。
6. **多 Agent 通信**：agent 之间消息路由、协调者-子 agent 委派。
7. **会话与记忆**：会话历史持久化、跨会话 memory、上下文压缩。
8. **多租户与安全**：org / user、API Key、RBAC、凭据加密存储（MCP / Webhook / Provider / IM 密钥）。
9. **可观测性**：运行 trace、token / 成本统计、审计日志、结构化日志。

---

## 3. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 语言/运行时 | Python 3.12 | async-first |
| Web 框架 | **FastAPI** + Uvicorn（生产用 Gunicorn 管 worker） | 同时满足 REST / SSE / webhook |
| 数据校验/配置 | Pydantic v2 + pydantic-settings | DTO 与环境配置 |
| ORM/迁移 | **SQLAlchemy 2.0 (async)** + asyncpg + Alembic | PostgreSQL |
| 任务队列 | **Postgres 原生队列**（`procrastinate` 或自建 `SELECT … FOR UPDATE SKIP LOCKED`） | 不引入 Redis 也能跑，契合"外部仅 PG" |
| 缓存/总线（可选） | Redis（pub/sub、多实例 SSE 扇出、多 agent 消息、限流） | 单实例 MVP 可不要；多实例推荐 |
| LLM Provider | `anthropic`（默认，`claude-opus-4-8`，adaptive thinking）；`openai`（可选） | 见 §4.3 |
| MCP | MCP Python SDK（client 角色） | 连接外部 MCP server |
| HTTP 客户端 | httpx | Webhook 工具、IM 出站 |
| 鉴权 | API Key + JWT（authlib / python-jose）、passlib | 控制台用户 + 程序调用 |
| 容器 | 单 Docker 镜像，入口按 `ROLE=web|worker` 切换进程 | 外部 PG；compose 仅做本地编排 |
| 测试 | pytest、pytest-asyncio、testcontainers(PG) | 端到端 |

### Claude Provider 约定
默认模型 `claude-opus-4-8`，使用 `thinking={"type":"adaptive"}` + `output_config={"effort": ...}`；流式用 `messages.stream()` + `get_final_message()`；工具调用走原生 tool-use。多模型抽象层在其上做规范化。

---

## 4. 模块架构

```
┌──────────────────────────────────────────────────────────────┐
│  接入层 (FastAPI)                                              │
│  - 管理 API (CRUD: agent/prompt/mcp/skill/webhook/key)         │
│  - 调用 API (同步 invoke / 异步 run / SSE stream)              │
│  - IM 入站 webhook (slack/telegram/discord)                   │
│  - Auth 中间件 (API Key / JWT)                                 │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
   ┌────────────▼───────────┐      ┌───────────▼─────────────┐
   │ Agent 注册/配置中心     │      │ IM 渠道层 (connectors)   │
   │ - agent 定义 + 版本     │      │ - 入站归一化/出站发送    │
   │ - 能力绑定 (mcp/skill/  │      │ - 身份映射/会话续接      │
   │   webhook/prompt)       │      └───────────┬─────────────┘
   └────────────┬───────────┘                  │
                │                              │
   ┌────────────▼──────────────────────────────▼───────────────┐
   │ Agent 运行时 / 编排引擎 (Orchestration Engine)             │
   │ - agentic loop: 组装 prompt → 调 Provider → 处理 tool_use   │
   │   → 执行工具 → 回灌结果 → 循环到 end_turn                   │
   │ - 上下文管理(历史/压缩/token 预算)、流式事件                │
   │ - 工具执行器 (Tool Executor) 分发到 ↓                       │
   └──┬─────────────┬──────────────┬─────────────┬──────────────┘
      │             │              │             │
 ┌────▼───┐   ┌─────▼────┐   ┌─────▼────┐  ┌─────▼─────┐
 │Provider│   │MCP client│   │ Skill    │  │ Webhook   │
 │抽象层  │   │ manager  │   │ engine   │  │ tool      │
 │(claude │   └──────────┘   └──────────┘  └───────────┘
 │/openai)│
 └────────┘
   ┌──────────────────────────────────────────────────────────┐
   │ 横切: 会话&记忆 / 多agent总线 / 任务队列&worker /          │
   │       多租户&密钥库 / 可观测性                             │
   └──────────────────────────────────────────────────────────┘
        持久化: PostgreSQL (SQLAlchemy + Alembic)
```

### 4.1 接入层 (`app/api`)
路由、鉴权、请求/响应 DTO。调用 API 三形态：

| 形态 | 端点 | 行为 |
|---|---|---|
| 同步 | `POST /v1/agents/{id}/invoke` | 阻塞执行 agentic loop，返回最终结果 |
| 异步 | `POST /v1/agents/{id}/runs` → `GET /v1/runs/{run_id}` | 入队，worker 执行，轮询结果 + 完成回调 webhook |
| 流式 | `GET /v1/runs/{run_id}/stream` | SSE 推送 token / 工具事件 / 状态 |

### 4.2 Agent 注册/配置中心 (`app/agents`)
agent 定义、版本快照、能力绑定的 CRUD 与解析。运行前把绑定的 prompt / MCP / skill / webhook 解析成运行时可用的工具集与系统提示词。

### 4.3 Provider 抽象层 (`app/providers`)
统一接口 `LLMProvider`：

```python
class LLMProvider(Protocol):
    async def generate(self, req: GenRequest) -> GenResult: ...
    def stream(self, req: GenRequest) -> AsyncIterator[StreamEvent]: ...
```

- 入参/出参统一为内部中立的 message / tool-call schema。
- 默认实现 `AnthropicProvider`；`OpenAIProvider` 等可插拔。
- 负责把各家 tool-call 格式规范化为统一形态，供 Tool Executor 消费。

### 4.4 运行时/编排引擎 (`app/runtime`)
核心 agentic loop + Tool Executor + 上下文管理 + 事件流。循环：组装 prompt（system + 历史 + 工具）→ 调 Provider → 若 `tool_use` 则经 Tool Executor 执行工具并回灌 `tool_result` → 直到 `end_turn`。上下文管理负责历史裁剪/压缩与 token 预算。

### 4.5 能力子系统 (`app/capabilities`)
`mcp/`（MCP client manager：连接、工具发现、调用、凭据）、`skills/`（Skill 引擎：渐进加载）、`webhooks/`（HTTP 接口转工具：入参 schema、鉴权、响应映射）、`prompts/`（模板 + 变量）。

### 4.6 IM 渠道层 (`app/channels`)
`base.py` 定义归一化接口（入站 → 内部 message，出站 ← agent 输出）；`slack/`、`telegram/`、`discord/` 适配器。处理 IM 用户身份映射与会话续接。

### 4.7 其他横切模块
- **会话&记忆 (`app/sessions`)**：会话、消息历史、memory store。
- **多 Agent 通信 (`app/multiagent`)**：消息总线（PG 队列或 Redis pub/sub）、agent 寻址、协调者-子 agent 委派协议。
- **任务队列&worker (`app/workers`)**：run 的异步执行、回调触发。
- **多租户&密钥库 (`app/auth`, `app/secrets`)**：org/user/key/RBAC、凭据加密（Fernet / 外部 KMS）。
- **可观测性 (`app/observability`)**：trace、usage/cost、审计、结构化日志。
- **持久化 (`app/db`)**：SQLAlchemy models、session、Alembic migrations。

---

## 5. 数据模型（PostgreSQL 主要表）

| 域 | 表 |
|---|---|
| 多租户/鉴权 | `orgs`, `users`, `api_keys` |
| Agent | `agents`, `agent_versions` |
| 能力定义 | `prompts`, `mcp_servers`, `skills`, `webhook_tools` |
| 能力绑定 | `agent_capability_bindings`（agent ↔ 能力 多对多） |
| 凭据 | `credentials`（加密：provider / mcp / webhook / im） |
| 会话 | `sessions`, `messages` |
| 运行 | `runs`, `run_events`（异步运行实例 + 流式事件/trace） |
| 记忆 | `memories`（跨会话） |
| IM | `im_channels`, `im_identities`（接入配置 + 用户身份映射） |
| 多 agent | `agent_messages` |
| 运营 | `usage_records`, `audit_logs` |

---

## 6. 典型流程

### 6.1 同步调用
```
Client → POST /v1/agents/{id}/invoke
       → 解析 agent 配置(prompt+工具) → Runtime agentic loop
         → Provider.generate → (tool_use? → ToolExecutor → 回灌) → end_turn
       ← 最终结果 + usage
```

### 6.2 异步 + 流式
```
Client → POST /v1/agents/{id}/runs  → 创建 run(入 PG 队列) → 返回 run_id
Worker → 取 run → Runtime loop → 写 run_events → 完成时触发回调 webhook
Client → GET /v1/runs/{run_id}/stream (SSE) → 实时消费 run_events
```

### 6.3 IM 接入
```
Slack/TG/Discord → 平台 webhook → channels 适配器(归一化+身份映射)
                 → 复用对应 session → Runtime loop → 出站适配器回复
```

### 6.4 多 Agent 通信
```
Agent A (协调者) → multiagent 总线(addr=Agent B) → Agent B run
                ← 结果消息回灌 A 的上下文
```

---

## 7. 目录骨架（建议，后续迭代落地）

```
open-agent/
├── app/
│   ├── main.py                # FastAPI app 工厂；ROLE=web/worker 入口
│   ├── config.py              # pydantic-settings
│   ├── api/                   # 路由 (admin / invoke / runs / im_webhooks)
│   ├── agents/                # 注册/配置中心
│   ├── providers/             # LLMProvider 抽象 + anthropic/openai 实现
│   ├── runtime/               # agentic loop + tool executor + 上下文
│   ├── capabilities/          # mcp / skills / webhooks / prompts
│   ├── channels/              # slack / telegram / discord 适配器
│   ├── sessions/              # 会话 & memory
│   ├── multiagent/            # agent 间通信总线
│   ├── workers/               # 异步 run 执行
│   ├── auth/  secrets/        # 鉴权 + 密钥库
│   ├── observability/         # trace / usage / 日志
│   └── db/                    # SQLAlchemy models + session + alembic/
├── tests/
├── alembic.ini
├── pyproject.toml
├── Dockerfile                 # 单镜像，entrypoint 按 ROLE 切换
├── docker-compose.yml         # 本地: app(web) + app(worker) + postgres [+ redis]
├── .env.example
└── docs/ARCHITECTURE.md
```

---

## 8. 部署形态

- **单 Docker 镜像**：同一镜像通过 `ROLE` 环境变量切换为 `web`（FastAPI/Uvicorn）或 `worker`（任务消费）进程。
- **外部 PostgreSQL**：作为外部依赖，连接串通过环境变量注入。
- **Redis 可选**：单实例 MVP 可省略；多实例水平扩展时用于 SSE 扇出、多 agent pub/sub、限流。
- 本地 `docker-compose.yml` 编排：`app(web)` + `app(worker)` + `postgres`（+ 可选 `redis`）。

后续迭代里程碑见 [ROADMAP.md](./ROADMAP.md)。
