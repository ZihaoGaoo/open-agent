# open-agent · 迭代路线图

总体设计见 [ARCHITECTURE.md](./ARCHITECTURE.md)。本路线图把"后续细化各模块及实现"拆为四个里程碑，逐步交付可运行的能力。

## M1 · 基础框架 + Provider + 同步调用
**目标**：跑通"创建 agent → 绑定 prompt → 同步调用 → 拿到结果"的最小闭环。
- 工程脚手架：`pyproject.toml`、`Dockerfile`（`ROLE=web/worker`）、`docker-compose.yml`、`.env.example`。
- `app/db`：SQLAlchemy 2.0 async + Alembic，落地 `orgs/users/api_keys/agents/agent_versions/prompts` 等核心表。
- `app/auth`：API Key 鉴权中间件。
- `app/providers`：`LLMProvider` 抽象 + `AnthropicProvider`（`claude-opus-4-8`，adaptive thinking）。
- `app/runtime`：基础 agentic loop（暂无外部工具）。
- `app/api`：`POST /v1/agents/{id}/invoke`（同步）+ agent/prompt 管理 CRUD。
- **验收**：起容器 + 外部 PG，创建 agent 绑定 prompt，调用 invoke 返回结果。

## M2 · 能力子系统（MCP / Skill / Webhook）
**目标**：agent 可挂载并调用三类外部能力。
- `app/capabilities/mcp`：MCP client manager（stdio/HTTP、工具发现与调用）。
- `app/capabilities/webhooks`：HTTP 接口转工具（入参 schema、鉴权、响应映射）。
- `app/capabilities/skills`：Skill 引擎（`SKILL.md` 渐进加载）。
- `app/capabilities/prompts`：模板 + 变量插值（完善）。
- `app/secrets`：凭据加密存储（Fernet）；`credentials`、`agent_capability_bindings` 表。
- `app/runtime`：Tool Executor 分发到三类能力 + 上下文管理/压缩。
- **验收**：agent 绑定一个 MCP server + 一个 webhook 工具，loop 中正确调用并回灌结果。

## M3 · 异步/流式 + IM 接入
**目标**：支持异步 run、SSE 流式，以及 Slack/Telegram/Discord 双向接入。
- `app/workers`：PG 原生任务队列 + run 执行；`runs`、`run_events` 表。
- `app/api`：`POST /v1/agents/{id}/runs`、`GET /v1/runs/{run_id}`、`GET /v1/runs/{run_id}/stream`（SSE）、完成回调 webhook。
- `app/sessions`：会话与历史持久化、memory store。
- `app/channels`：`base` 归一化 + Slack / Telegram / Discord 适配器；`im_channels`、`im_identities` 表。
- **验收**：异步提交 run 并通过 SSE 实时消费；从 IM 发消息触发 agent 并收到回复。

## M4 · 多 Agent 通信 + 可观测性 + 多租户完善
**目标**：补齐 agent 间协作、运营观测与 RBAC。
- `app/multiagent`：消息总线（PG 队列；多实例可选 Redis pub/sub）、寻址、协调者-子 agent 委派；`agent_messages` 表。
- `app/observability`：trace、token/成本统计、审计日志、结构化日志；`usage_records`、`audit_logs` 表。
- `app/auth`：RBAC、控制台用户 JWT、多租户隔离完善。
- **验收**：一个协调者 agent 委派子 agent 完成子任务并回收结果；运营面板可见 trace 与成本。

---

> 里程碑顺序可按业务优先级调整；每个里程碑结束应保持平台可独立运行与演示。
