"""Provider 注册表：按名称解析 Provider 实例（默认 anthropic）。

新增厂商：实现 LLMProvider 接口后用 register_provider 注册即可。
"""

from __future__ import annotations

from collections.abc import Callable

from app.providers.base import LLMProvider

_FACTORIES: dict[str, Callable[[], LLMProvider]] = {}


def register_provider(name: str, factory: Callable[[], LLMProvider]) -> None:
    _FACTORIES[name] = factory


def get_provider(name: str = "anthropic") -> LLMProvider:
    if name not in _FACTORIES:
        raise KeyError(f"未注册的 provider: {name!r}（可用: {sorted(_FACTORIES)}）")
    return _FACTORIES[name]()


def _default_anthropic() -> LLMProvider:
    from app.providers.anthropic_provider import AnthropicProvider

    return AnthropicProvider()


register_provider("anthropic", _default_anthropic)
