"""能力子系统：把外部能力规范化为运行时可调用的工具/提示词。

- prompts:  提示词模板 + 变量插值
- mcp:      MCP server 连接、工具发现与调用 (M2)
- skills:   文件系统 Skill 渐进加载 (M2)
- webhooks: HTTP 接口转工具 (M2)
"""
