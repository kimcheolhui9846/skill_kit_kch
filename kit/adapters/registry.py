"""Name -> adapter. Adding an agent = one adapter class + one entry here (REQ-ARCH-003)."""

from __future__ import annotations

from typing import Dict, List

from .base import AgentAdapter
from .claude import ClaudeAdapter
from .codex import CodexAdapter

_ADAPTERS: Dict[str, AgentAdapter] = {"codex": CodexAdapter(), "claude": ClaudeAdapter()}


def names() -> List[str]:
    return sorted(_ADAPTERS)


def get(name: str) -> AgentAdapter:
    try:
        return _ADAPTERS[name]
    except KeyError:
        raise KeyError(f"unknown agent '{name}' (known: {', '.join(names())})") from None


def register(adapter: AgentAdapter) -> None:
    _ADAPTERS[adapter.name] = adapter


def unregister(name: str) -> None:
    _ADAPTERS.pop(name, None)
