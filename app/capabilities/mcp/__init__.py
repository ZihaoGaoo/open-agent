"""MCP client manager（M2）。

职责：连接 MCP server（stdio / HTTP），发现工具并暴露为 ToolDef，
在运行时被调用时转发到对应 server。凭据经 app.secrets 解密注入。
"""
