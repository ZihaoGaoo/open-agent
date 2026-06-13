"""提示词模板渲染。"""

from __future__ import annotations

from string import Template
from typing import Any


def render_prompt(template: str, variables: dict[str, Any] | None = None) -> str:
    """用 $var 占位符做安全插值；缺失变量保持原样。"""
    if not variables:
        return template
    return Template(template).safe_substitute(variables)
