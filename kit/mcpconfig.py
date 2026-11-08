"""MCP server data (manifest/allowlist) and the kit block inside <target>/.codex/config.toml."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .model import CONFLICT, FAIL, PASS, UNVERIFIED, ItemResult, UsageError
from .writers.markdown_block import MarkerError, extract_block
from .writers.toml_block import BEGIN, END, parse_toml
from .writers.toml_block import without_block as _without_block

CONFIG_REL = ".codex/config.toml"
TRUST_NOTE = "Codex loads .codex/config.toml only for trusted projects"
STALE_DETAIL = (
    "kit MCP block from an earlier run is still registered; delete the lines from "
    "'# hackathon-kit:begin' to '# hackathon-kit:end' in .codex/config.toml "
    "if you do not want it"
)
_HEADER = re.compile(
    r'^[ \t]*\[[ \t]*mcp_servers[ \t]*\.[ \t]*"?([A-Za-z0-9_-]+)"?[ \t]*\]', re.MULTILINE
)


def _load(kit_root: Path, name: str) -> dict:
    return json.loads((kit_root / "mcp" / name).read_text(encoding="utf-8"))


def load_manifest(kit_root: Path) -> dict:
    return _load(kit_root, "manifest.json")


def load_allowlist(kit_root: Path) -> dict:
    return _load(kit_root, "allowlist.json")


class McpSelection(list):
    """Server names already chosen from catalog/mcp.json (new path, kit.mcp_catalog).

    A plain list of names everywhere a profile's mcp list is used; the catalog entries travel
    with it so select_servers() does not fall back to mcp/manifest.json.
    """

    def __init__(self, items=()):
        items = list(items)
        super().__init__(name for name, _ in items)
        self.entries = dict(items)

    def merged(self, other: "McpSelection") -> "McpSelection":
        extra = [(n, other.entries[n]) for n in other if n not in self.entries]
        return McpSelection([(n, self.entries[n]) for n in self] + extra)


def select_servers(kit_root: Path, names: list[str]) -> list[tuple[str, dict]]:
    if isinstance(names, McpSelection):
        return [(name, names.entries[name]) for name in names]
    if not names:
        return []
    servers = load_manifest(kit_root)["servers"]
    allowed = set(load_allowlist(kit_root)["servers"])
    selected = []
    for name in names:
        entry = servers.get(name)
        if entry is None or not entry.get("enabled_by_default") or name not in allowed:
            raise UsageError(
                f"MCP server '{name}' is not enabled in mcp/manifest.json and mcp/allowlist.json"
            )
        selected.append((name, entry))
    return selected


def _env_vars(entry: dict) -> list:
    """P4-T9: API keys are passed through from the shell by name; no value is written."""
    names = [c["env"] for c in entry.get("credentials") or []]
    return [f"env_vars = [{', '.join(json.dumps(n) for n in names)}]"] if names else []


def render_servers(servers: list[tuple[str, dict]]) -> str:
    blocks = []
    for name, entry in servers:
        args = ", ".join(json.dumps(arg) for arg in entry["args"])
        blocks.append(
            "\n".join(
                [
                    f"[mcp_servers.{name}]",
                    f"command = {json.dumps(entry['command'])}",
                    f"args = [{args}]",
                    f"startup_timeout_sec = {int(entry.get('startup_timeout_sec', 30))}",
                ]
                + _env_vars(entry)
            )
        )
    return "\n\n".join(blocks)


def _preserved(old: dict, new: dict) -> bool:
    for key, value in old.items():
        if key == "mcp_servers" and isinstance(value, dict):
            new_servers = new.get("mcp_servers", {})
            if any(new_servers.get(name) != cfg for name, cfg in value.items()):
                return False
        elif new.get(key) != value:
            return False
    return True


def check_merged(new_text: str, names: list[str]) -> str | None:
    """Return why the merged config must not be written, or None when it is safe."""
    try:
        outside = _without_block(new_text)
    except MarkerError as exc:
        return str(exc)
    duplicates = sorted(set(_HEADER.findall(outside)) & set(names))
    if duplicates:
        return f"MCP server '{duplicates[0]}' is already defined outside the kit block"
    status, new_data, error = parse_toml(new_text)
    if status is False:
        return f"merged config.toml would not be valid TOML: {error}"
    if status:
        _, old_data, _ = parse_toml(outside)
        if old_data is not None and not _preserved(old_data, new_data):
            return "merging would change existing config.toml settings"
    return None


def stale_block_item(target: Path) -> ItemResult | None:
    """Optional FAIL when a kit block from an earlier run is left while MCP is excluded."""
    try:
        text = (target / CONFIG_REL).read_bytes().decode("utf-8")
        found = extract_block(text, BEGIN, END)
    except (OSError, UnicodeDecodeError, MarkerError):
        return None
    if found is None:
        return None
    return ItemResult("mcp-config", False, True, True, FAIL, STALE_DETAIL)


def verify_config(
    target: Path, kit_root: Path, names: list[str], conflict_detail: str | None
) -> ItemResult:
    label = "mcp-config"
    if conflict_detail:
        return ItemResult(label, False, True, False, CONFLICT, conflict_detail)
    path = target / CONFIG_REL
    if not path.is_file():
        return ItemResult(label, False, False, False, FAIL, f"{CONFIG_REL} missing")
    try:
        text = path.read_bytes().decode("utf-8")
        found = extract_block(text, BEGIN, END)
    except (OSError, UnicodeDecodeError, MarkerError) as exc:
        return ItemResult(label, False, True, False, FAIL, str(exc))
    if found is None:
        return ItemResult(label, False, True, False, FAIL, "kit block missing")
    if found[2] != render_servers(select_servers(kit_root, names)).strip():
        return ItemResult(label, False, True, True, FAIL, "kit block is outdated")
    status, _, error = parse_toml(text)
    if status is None:
        detail = f"TOML parse check needs Python 3.11+; {TRUST_NOTE}"
        return ItemResult(label, False, True, True, UNVERIFIED, detail)
    if status is False:
        return ItemResult(label, False, True, True, FAIL, f"not valid TOML: {error}")
    return ItemResult(label, False, True, True, PASS, TRUST_NOTE)
