"""Adapters for --scope user (P4-T7, ADR-018, 04_DESIGN §2.3 user columns).

The target is the home folder; every path is relative to it (".codex/AGENTS.md"). What gets
installed is described in kit.userscope. Rules that differ from project scope:
- A file or JSON key that already has the kit's content but was not written by the kit is
  left alone and not recorded, so uninstall never removes something another tool (or the
  user) put there. A different file at a kit path is a CONFLICT (e.g. OMX installed by
  `omx setup`), never overwritten.
- No MCP handshake, no tools, no plugin CLI: those are per workspace.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Dict, List, Optional

from .. import userscope
from ..fsops import State, sha256
from ..mcpconfig import render_servers, select_servers
from ..mcpjson import _read as read_json
from ..mcpjson import plan_owned_keys, record_key, verify_owned_keys
from ..model import CONFLICT, FAIL, PASS, ItemResult, Outcome, UsageError
from ..plan import FileChange, _plan_block, plan_file, skill_target_files
from ..verify import _verify_agents_md, _verify_skill
from ..writers import json_keys, markdown_block, toml_block
from ..writers.markdown_block import MarkerError, extract_block
from ..writers.toml_block import parse_toml, without_block
from .base import BlockTarget

OMX_OWNER = "omx"
OWN_OWNER = "own"  # user/codex/own (Q4)
CONFIG_OWNER = "user-config"
SETTINGS_OWNER = "user-settings"


def _not_adopted(changes: List[FileChange], state: State) -> None:
    """Same content already there, not from the kit: leave it unowned."""
    for change in changes:
        if (
            change.outcome == Outcome.UNCHANGED
            and change.record is not None
            and change.rel not in state.files
            and not change.extra_records
            and (change.owner.startswith("skill:") or change.owner in (OMX_OWNER, OWN_OWNER))
        ):
            change.record = None
            change.detail = "already present, not written by the kit (left unowned)"


def _skills(target, kit_root, profile, state, skill_root, skill_source) -> List[FileChange]:
    out = []
    for name in profile.skills:
        for rel, data in skill_target_files(kit_root, name, skill_root, skill_source):
            out.append(plan_file(target, rel, f"skill:{name}", data, state))
    return out


def _owned_items(changes: List[FileChange], owner: str, label: str, what: str) -> ItemResult:
    mine = [c for c in changes if c.owner == owner]
    conflicts = [c for c in mine if c.outcome == Outcome.CONFLICT]
    if conflicts:
        detail = (
            f"{len(conflicts)} of {len(mine)} {what} exist and were not written by the kit "
            f"(first: {conflicts[0].rel}); left untouched"
        )
        return ItemResult(label, False, True, False, CONFLICT, detail)
    return ItemResult(label, False, True, True, PASS, f"{len(mine)} {what}")


def _server_of(table: str) -> Optional[str]:
    """'mcp_servers.x' or 'mcp_servers.x.env' -> 'x'."""
    parts = userscope.split_name(table)
    if len(parts) >= 2 and parts[0] == "mcp_servers":
        return parts[1].strip("\"'")
    return None


class _UserBase:
    scope = "user"
    mcp_cli_check = False

    def __init__(self, home: Path):
        self.home = home
        self.dir = userscope.agent_dir(self.name, home)
        self._manual: List[str] = []

    def audit(self, target: Path, kit_root: Path, allowlist: Optional[dict] = None):
        return None  # the home config is the user's own; kit entries come from the catalog

    def stale_mcp(self, target: Path) -> Optional[ItemResult]:
        return None


class CodexUserAdapter(_UserBase):
    name = "codex"
    display_name = "Codex"
    cli = "codex"

    def __init__(self, home: Path):
        super().__init__(home)
        self.policy = BlockTarget(f"{self.dir}/AGENTS.md", markdown_block.BEGIN, markdown_block.END)
        self.skill_root = f"{self.dir}/skills"
        self.mcp_config = BlockTarget(f"{self.dir}/config.toml", toml_block.BEGIN, toml_block.END)

    # ------------------------------------------------------------ config.toml block

    def config_body(self, target: Path, kit_root: Path, servers, outside: str) -> tuple:
        """(kit block body, notes, conflict). Captured tables already set the same way outside
        the block are left out; set differently, they are a conflict."""
        parts, notes = [], []
        if servers:
            parts.append(render_servers(select_servers(kit_root, servers)).strip())
        captured = userscope.codex_tables(kit_root, self.home)
        outside_tables = dict((n, t) for n, t in userscope.split_tables(outside) if n is not None)
        names = set(servers or [])
        clash = sorted(n for n in outside_tables if _server_of(n) in names)
        if clash:
            return "", notes, f"[{clash[0]}] is already defined outside the kit block"
        if captured:
            keep = []
            for name, text in userscope.split_tables(captured):
                if name is None:
                    continue
                if name in outside_tables:
                    a = parse_toml(outside_tables[name])
                    b = parse_toml(text)
                    if a[0] and b[0] and a[1] == b[1]:
                        notes.append(f"[{name}] already set the same way")
                        continue
                    return "", notes, f"[{name}] is already set differently outside the kit block"
                keep.append(text.strip())
            if keep:
                parts.append("\n\n".join(keep))
        return "\n\n".join(parts), notes, None

    def _plan_config(self, target, kit_root, servers, state) -> Optional[FileChange]:
        rel = self.mcp_config.rel
        path = target / rel
        try:
            text = path.read_bytes().decode("utf-8") if path.is_file() else ""
            outside = without_block(text)
        except (OSError, UnicodeDecodeError, MarkerError) as exc:
            return FileChange(rel, CONFIG_OWNER, Outcome.CONFLICT, detail=str(exc))
        body, _, conflict = self.config_body(target, kit_root, servers, outside)
        if conflict:
            return FileChange(rel, CONFIG_OWNER, Outcome.CONFLICT, detail=conflict)
        if not body:
            return None
        change = _plan_block(target, rel, CONFIG_OWNER, body, state, *self._markers())
        if change.data is not None:
            ok, _, error = parse_toml(change.data.decode("utf-8"))
            if ok is False:
                return FileChange(
                    rel,
                    CONFIG_OWNER,
                    Outcome.CONFLICT,
                    detail=f"merged config.toml would not be valid TOML: {error}",
                )
        return change

    def _markers(self):
        return self.mcp_config.begin, self.mcp_config.end

    # ------------------------------------------------------------ plan / verify

    def plan(
        self,
        target,
        kit_root,
        profile,
        state,
        include_mcp,
        policy_body=None,
        skill_source=None,
        plugins=None,
    ) -> List[FileChange]:
        changes: List[FileChange] = []
        body = userscope.policy_block(kit_root, "codex", self.home)
        if body:
            changes.append(
                _plan_block(
                    target,
                    self.policy.rel,
                    self.policy.rel,
                    body,
                    state,
                    self.policy.begin,
                    self.policy.end,
                )
            )
        omx = userscope.omx_skill_names(kit_root)
        clash = sorted(set(omx) & set(profile.skills))
        if clash:
            raise UsageError(f"skill '{clash[0]}' is both a kit skill and an OMX skill")
        own = userscope.own_skill_names(kit_root)
        clash = sorted(set(own) & (set(omx) | set(profile.skills)))
        if clash:
            raise UsageError(
                f"skill '{clash[0]}' in {userscope.OWN_DIR} is also a kit or OMX skill"
            )
        changes += _skills(target, kit_root, profile, state, self.skill_root, skill_source)
        for rel, _, data in userscope.omx_files(kit_root, self.dir):
            changes.append(plan_file(target, rel, OMX_OWNER, data, state))
        for rel, _, data in userscope.own_files(kit_root, self.dir):
            changes.append(plan_file(target, rel, OWN_OWNER, data, state))
        config = self._plan_config(target, kit_root, profile.mcp if include_mcp else [], state)
        if config is not None:
            changes.append(config)
        _not_adopted(changes, state)
        return changes

    def verify(
        self,
        target,
        kit_root,
        profile,
        changes,
        check_writable,
        writable,
        include_mcp,
        policy_body=None,
        skill_source=None,
        plugins=None,
    ):
        conflicts = {
            c.owner: f"{c.rel}: {c.detail}" for c in changes if c.outcome == Outcome.CONFLICT
        }
        items = []
        body = userscope.policy_block(kit_root, "codex", self.home)
        if body:
            items.append(_verify_agents_md(target, kit_root, conflicts, self.policy.rel, body))
        for name in profile.skills:
            items.append(
                _verify_skill(
                    target,
                    kit_root,
                    name,
                    name in profile.required_skills,
                    conflicts,
                    self.skill_root,
                    skill_source,
                )
            )
        items.append(self._verify_omx(target, kit_root, changes))
        if userscope.own_files(kit_root, self.dir):
            items.append(self._verify_own(target, kit_root, changes))
        items += self._verify_config(
            target, kit_root, profile.mcp if include_mcp else [], conflicts.get(CONFIG_OWNER)
        )
        return items

    def _verify_omx(self, target, kit_root, changes) -> ItemResult:
        label = "omx"
        if any(c.owner == OMX_OWNER and c.outcome == Outcome.CONFLICT for c in changes):
            return _owned_items(changes, OMX_OWNER, label, "OMX files")
        files = userscope.omx_files(kit_root, self.dir)
        for rel, _, data in files:
            path = target / rel
            if not path.is_file():
                return ItemResult(label, False, False, False, FAIL, f"{rel} missing")
            if sha256(path.read_bytes()) != sha256(data):
                return ItemResult(label, False, True, False, FAIL, f"{rel} differs")
        detail = f"{len(files)} files (OMX skills and prompts, v0.21.46)"
        return ItemResult(label, False, True, True, PASS, detail)

    def _verify_own(self, target, kit_root, changes) -> ItemResult:
        label = "own"
        if any(c.owner == OWN_OWNER and c.outcome == Outcome.CONFLICT for c in changes):
            return _owned_items(changes, OWN_OWNER, label, "your own files")
        files = userscope.own_files(kit_root, self.dir)
        for rel, _, data in files:
            path = target / rel
            if not path.is_file():
                return ItemResult(label, False, False, False, FAIL, f"{rel} missing")
            if sha256(path.read_bytes()) != sha256(data):
                return ItemResult(label, False, True, False, FAIL, f"{rel} differs")
        detail = f"{len(files)} files (your own skills and prompts, {userscope.OWN_DIR})"
        return ItemResult(label, False, True, True, PASS, detail)

    def _verify_config(self, target, kit_root, servers, conflict) -> List[ItemResult]:
        label = self.mcp_config.rel
        if conflict:
            return [ItemResult(label, False, True, False, CONFLICT, conflict)]
        path = target / label
        try:
            text = path.read_bytes().decode("utf-8") if path.is_file() else ""
            found = extract_block(text, *self._markers())
            outside = without_block(text)
        except (OSError, UnicodeDecodeError, MarkerError) as exc:
            return [ItemResult(label, False, True, False, FAIL, str(exc))]
        body, notes, problem = self.config_body(target, kit_root, servers, outside)
        if problem:
            return [ItemResult(label, False, True, False, CONFLICT, problem)]
        if not body:
            return []
        if found is None:
            return [ItemResult(label, False, False, False, FAIL, "kit block missing")]
        if found[2] != body.strip():
            return [ItemResult(label, False, True, False, FAIL, "kit block is outdated")]
        detail = (
            "kit block: "
            + ", ".join(userscope.table_names(body))
            + (f"; {'; '.join(notes)}" if notes else "")
        )
        return [ItemResult(label, False, True, True, PASS, detail)]

    def manual_checks(self, target: Path) -> List[str]:
        return [
            f"Open Codex in any folder and run /skills: the kit and OMX skills in "
            f"~/{self.skill_root}/ should be listed."
        ]


def _env_ref(name: str) -> str:
    return name + "=${" + name + "}"


def claude_mcp_commands(kit_root: Path, servers) -> List[str]:
    """`claude mcp add --scope user` per catalog server; the kit never edits ~/.claude.json."""
    out = []
    for name, entry in select_servers(kit_root, servers):
        argv = [
            "claude",
            "mcp",
            "add",
            "--scope",
            "user",
            name,
            # P4-T9: a reference Claude expands at start (single-quoted, so no shell expands it)
            *[a for c in entry.get("credentials") or [] for a in ("-e", _env_ref(c["env"]))],
            "--",
            entry["command"],
            *entry["args"],
        ]
        out.append(" ".join(shlex.quote(a) for a in argv))
    return out


class ClaudeUserAdapter(_UserBase):
    name = "claude"
    display_name = "Claude Code"
    cli = "claude"
    mcp_manual = True  # ~/.claude.json is Claude's own file (ADR-018)

    def __init__(self, home: Path):
        super().__init__(home)
        self.policy = BlockTarget(f"{self.dir}/CLAUDE.md", markdown_block.BEGIN, markdown_block.END)
        self.skill_root = f"{self.dir}/skills"
        self.mcp_config = BlockTarget(f"{self.dir}/settings.json", "", "")
        self.settings_rel = f"{self.dir}/settings.json"

    def _keys(self, kit_root: Path) -> Dict[str, object]:
        return userscope.claude_settings(kit_root, self.home)

    def plan(
        self,
        target,
        kit_root,
        profile,
        state,
        include_mcp,
        policy_body=None,
        skill_source=None,
        plugins=None,
    ) -> List[FileChange]:
        changes: List[FileChange] = []
        body = userscope.policy_block(kit_root, "claude", self.home)
        if body:
            changes.append(
                _plan_block(
                    target,
                    self.policy.rel,
                    self.policy.rel,
                    body,
                    state,
                    self.policy.begin,
                    self.policy.end,
                )
            )
        changes += _skills(target, kit_root, profile, state, self.skill_root, skill_source)
        keys = self._keys(kit_root)
        if keys:
            change = plan_owned_keys(target, self.settings_rel, SETTINGS_OWNER, keys, state)
            self._drop_adopted_keys(target, change, keys, state)
            changes.append(change)
        servers = profile.mcp if include_mcp else []
        self._manual = claude_mcp_commands(kit_root, servers) if servers else []
        _not_adopted(changes, state)
        return changes

    def _drop_adopted_keys(self, target, change: FileChange, keys, state: State) -> None:
        """A key that already has the value, set by the user, stays theirs."""
        if not change.extra_records:
            return
        text, _ = read_json(target, self.settings_rel)
        try:
            doc = json.loads(text) if text else {}
        except ValueError:
            return
        for pointer, value in keys.items():
            key = record_key(pointer, self.settings_rel)
            node: object = doc
            for part in json_keys.parse_pointer(pointer):
                node = node.get(part, json_keys._MISSING) if isinstance(node, dict) else None
            if node == value and key not in state.files:
                change.extra_records.pop(key, None)

    def verify(
        self,
        target,
        kit_root,
        profile,
        changes,
        check_writable,
        writable,
        include_mcp,
        policy_body=None,
        skill_source=None,
        plugins=None,
    ):
        conflicts = {
            c.owner: f"{c.rel}: {c.detail}" for c in changes if c.outcome == Outcome.CONFLICT
        }
        items = []
        body = userscope.policy_block(kit_root, "claude", self.home)
        if body:
            items.append(_verify_agents_md(target, kit_root, conflicts, self.policy.rel, body))
        for name in profile.skills:
            items.append(
                _verify_skill(
                    target,
                    kit_root,
                    name,
                    name in profile.required_skills,
                    conflicts,
                    self.skill_root,
                    skill_source,
                )
            )
        keys = self._keys(kit_root)
        if keys:
            items.append(
                verify_owned_keys(
                    target,
                    self.settings_rel,
                    self.settings_rel,
                    keys,
                    conflicts.get(SETTINGS_OWNER),
                    f"{len(keys)} captured setting(s)",
                )
            )
        return items

    def manual_checks(self, target: Path) -> List[str]:
        steps = [
            f"Open Claude Code in any folder and run /skills: the kit skills in "
            f"~/{self.skill_root}/ should be listed."
        ]
        steps += [
            f"Add the user MCP server yourself (the kit does not edit ~/.claude.json): {cmd}"
            for cmd in self._manual
        ]
        return steps


def adapter_for(name: str, home: Path):
    return {"codex": CodexUserAdapter, "claude": ClaudeUserAdapter}[name](home)
