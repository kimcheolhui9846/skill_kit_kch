"""Skill catalog and layered skill files for the new path (P4-T1, ADR-001, 04_DESIGN §3.6).

A skill is built from layers, like a tree: lower layers are shared, higher layers are narrower.

    1. base     catalog "location"  (.agents/skills/<n> | shared/skills/<n> | third_party/...)
                every agent the entry lists gets it
    2. overlay  catalog "overlay", only for the policies in "overlay_policies" (Q7)
    3. agent    <agent>/skills/<n>/  e.g. codex/skills/<n>/agents/openai.yaml
                only that agent gets it

A higher layer adds files and replaces a lower file with the same path. A file named
`<path>.append` is instead appended to `<path>` from the layers below (it must exist there).
An agent-only skill has no "location": all its files come from <agent>/skills/<n>/.

Other catalog fields (P4-T4):
- "include": {"<path in the skill>": "<kit file>"} adds single files to the base layer, e.g.
  the upstream LICENSE next to a vendored skill.
- "replaces": on the policies this entry serves, it takes the place of these skills in a
  profile (D-20 replace-in-standard). The kit's own skills then name the replacement: their
  Markdown mentions of a replaced skill are rewritten when installed (rename_mentions).
- "requires": skills that must be installed with this one (its links or scripts reach into
  ../<name>/). The checker then allows such links.
- "packs": the skill joins any selected profile or pack with one of these names, when it is
  available for the agent and policy.
- The same name may be listed twice when the policies do not overlap (e.g. the kit's
  systematic-debugging for restricted, the vendored one for standard).
- Files taken from third_party/ are compared with sources.lock.json before every install.

The legacy path never reads this module; it copies .agents/skills as before (golden tests).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .fsops import path_order
from .profiles import ProfileError

CATALOG_REL = "catalog/skills.json"
THIRD_PARTY = "third_party"
SCHEMA = 1
POLICIES = ("restricted", "standard")
APPEND = ".append"
_FIELDS = {
    "name",
    "location",
    "origin",
    "agents",
    "packs",
    "policies",
    "overlay",
    "overlay_policies",
    "replaces",
    "include",
    "requires",
    "credentials",
}
DEFAULT_PACKS = ("core", "hitl")  # what --profile core,hitl installs (ADR-008)


class CatalogError(ProfileError):
    """catalog/skills.json is malformed or points at missing files (BLOCKED, like profiles)."""


@dataclass
class SkillEntry:
    name: str
    location: Optional[str]
    agents: List[str]
    policies: List[str]
    packs: List[str] = field(default_factory=list)
    origin: str = "kit"
    overlay: Optional[str] = None
    overlay_policies: List[str] = field(default_factory=list)
    replaces: List[str] = field(default_factory=list)
    include: Dict[str, str] = field(default_factory=dict)
    requires: List[str] = field(default_factory=list)
    credentials: List[dict] = field(default_factory=list)  # API keys set later (P4-T9)

    def available(self, agent: str, policy: str) -> Optional[str]:
        """None when the skill applies; otherwise why it is skipped."""
        if agent not in self.agents:
            return f"not for {agent}"
        if policy not in self.policies:
            return f"not in the {policy} policy"
        return None


def agent_layer(name: str, agent: str) -> str:
    return f"{agent}/skills/{name}"


def _agents() -> List[str]:
    from .adapters import registry  # late import (adapters import plan)

    return registry.names()


def _names(where: str, key: str, value: object, allowed=None) -> List[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise CatalogError(f"{where}: {key} must be a list of names")
    if allowed is not None:
        for item in value:
            if item not in allowed:
                raise CatalogError(f"{where}: unknown {key[:-1]} '{item}'")
    return list(value)


def _dir(kit_root: Path, where: str, rel: str) -> str:
    path = (kit_root / rel).resolve()
    root = kit_root.resolve()
    if root not in path.parents:
        raise CatalogError(f"{where}: '{rel}' is outside the kit")
    if not path.is_dir():
        raise CatalogError(f"{where}: '{rel}' does not exist")
    return rel


def _include(kit_root: Path, where: str, value: object) -> Dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise CatalogError(f"{where}: include must map skill paths to kit files")
    for inside, rel in value.items():
        if not inside or inside.startswith("/") or ".." in inside.split("/"):
            raise CatalogError(f"{where}: bad include path '{inside}'")
        path = (kit_root / rel).resolve()
        if kit_root.resolve() not in path.parents:
            raise CatalogError(f"{where}: '{rel}' is outside the kit")
        if not path.is_file():
            raise CatalogError(f"{where}: '{rel}' does not exist")
    return dict(value)


def _credentials(where: str, raw: dict) -> List[dict]:
    from . import credentials

    try:
        found = credentials.parse(where, raw.get("credentials"))
    except credentials.CredentialError as exc:
        raise CatalogError(str(exc)) from None
    if found and set(raw.get("packs", [])) & set(DEFAULT_PACKS):
        raise CatalogError(f"{where}: a skill that needs API keys cannot be in a default pack")
    return found


def load(kit_root: Path, policy: Optional[str] = None) -> Dict[str, SkillEntry]:
    """name -> entry. A name listed for disjoint policies resolves to the entry that serves
    `policy` (the first listing when policy is None or none serves it)."""
    chosen: Dict[str, SkillEntry] = {}
    for name, options in load_all(kit_root).items():
        pick = options[0]
        if policy is not None:
            pick = next((e for e in options if policy in e.policies), options[0])
        chosen[name] = pick
    return chosen


def load_all(kit_root: Path) -> Dict[str, List[SkillEntry]]:
    path = kit_root / CATALOG_REL
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError:
        raise CatalogError(f"{CATALOG_REL} is missing") from None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CatalogError(f"{CATALOG_REL} is not valid JSON: {exc}") from None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise CatalogError(f"{CATALOG_REL}: expected an object with schema {SCHEMA}")
    if not isinstance(data.get("skills"), list):
        raise CatalogError(f"{CATALOG_REL}: skills must be a list")
    agents = _agents()
    entries: Dict[str, List[SkillEntry]] = {}
    for raw in data["skills"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise CatalogError(f"{CATALOG_REL}: every skill needs a name")
        name = raw["name"]
        where = f"{CATALOG_REL} '{name}'"
        unknown = sorted(set(raw) - _FIELDS)
        if unknown:
            raise CatalogError(f"{where}: unknown field(s) {', '.join(unknown)}")
        entry = SkillEntry(
            name=name,
            location=raw.get("location"),
            agents=_names(where, "agents", raw.get("agents", agents), agents),
            policies=_names(where, "policies", raw.get("policies", ["standard"]), POLICIES),
            packs=_names(where, "packs", raw.get("packs", [])),
            origin=str(raw.get("origin", "kit")),
            overlay=raw.get("overlay"),
            overlay_policies=_names(
                where, "overlay_policies", raw.get("overlay_policies", []), POLICIES
            ),
            replaces=_names(where, "replaces", raw.get("replaces", [])),
            include=_include(kit_root, where, raw.get("include", {})),
            requires=_names(where, "requires", raw.get("requires", [])),
            credentials=_credentials(where, raw),
        )
        for other in entries.get(name, []):
            if set(other.policies) & set(entry.policies):
                raise CatalogError(f"{where}: listed twice for the same policy")
        if entry.location is not None:
            _dir(kit_root, where, entry.location)
            if not (kit_root / entry.location / "SKILL.md").is_file():
                raise CatalogError(f"{where}: {entry.location}/SKILL.md is missing")
        else:
            missing = [a for a in entry.agents if not (kit_root / agent_layer(name, a)).is_dir()]
            if missing:
                raise CatalogError(
                    f"{where}: no location, and no {agent_layer(name, missing[0])}/ either"
                )
        if entry.overlay is not None:
            _dir(kit_root, where, entry.overlay)
        if entry.overlay_policies and entry.overlay is None:
            raise CatalogError(f"{where}: overlay_policies without overlay")
        entries.setdefault(name, []).append(entry)
    for options in entries.values():
        for entry in options:
            for key in ("replaces", "requires"):
                for other in getattr(entry, key):
                    if other not in entries:
                        raise CatalogError(
                            f"{CATALOG_REL} '{entry.name}': {key} unknown skill '{other}'"
                        )
    return entries


def renames(entries: Dict[str, SkillEntry], agent: str, policy: str) -> Dict[str, str]:
    """old -> new for every skill this agent/policy cannot have and another entry replaces
    (the same choice commands._catalog_skills makes). Empty on restricted today."""
    out: Dict[str, str] = {}
    for name, entry in entries.items():
        if entry.available(agent, policy) is None:
            continue
        sub = next(
            (
                e.name
                for e in entries.values()
                if name in e.replaces and e.available(agent, policy) is None
            ),
            None,
        )
        if sub is not None:
            out[name] = sub
    return out


TEXT_SUFFIXES = (".md",)


def rename_mentions(files, mapping: Dict[str, str]) -> List[Tuple[str, bytes]]:
    """Point a kit skill's text at the skills that are actually installed: each whole-word
    mention of a replaced skill (`tdd-automator`, `../tdd-automator/...`) becomes its
    replacement. Only Markdown files; the kit's own skills only (never vendored text)."""
    if not mapping:
        return list(files)
    pattern = re.compile(
        r"(?<![\w-])("
        + "|".join(re.escape(n) for n in sorted(mapping, key=len, reverse=True))
        + r")(?![\w-])"
    )
    out = []
    for rel, data in files:
        if rel.endswith(TEXT_SUFFIXES):
            text = data.decode("utf-8")
            data = pattern.sub(lambda m: mapping[m.group(1)], text).encode("utf-8")
        out.append((rel, data))
    return out


def is_build_artifact(rel: Path) -> bool:
    """Bytecode a run of a bundled script leaves behind (P5-T6): never installed or checked."""
    return "__pycache__" in rel.parts or rel.suffix in (".pyc", ".pyo")


def _layer(root: Path) -> List[Tuple[str, bytes]]:
    return [
        (p.relative_to(root).as_posix(), p.read_bytes())
        for p in sorted(root.rglob("*"), key=path_order)
        if p.is_file() and not is_build_artifact(p.relative_to(root))
    ]


def skill_files(
    kit_root: Path, entry: SkillEntry, agent: str, policy: str
) -> List[Tuple[str, bytes]]:
    """[(path inside the skill folder, bytes)] after merging every layer for this agent."""
    layers: List[Path] = []
    if entry.location is not None:
        layers.append(kit_root / entry.location)
    if entry.overlay is not None and policy in entry.overlay_policies:
        layers.append(kit_root / entry.overlay)
    own = kit_root / agent_layer(entry.name, agent)
    if own.is_dir():
        layers.append(own)
    merged: Dict[str, bytes] = {}
    if entry.location is not None:  # base layer, then its single-file includes
        merged.update(_layer(layers.pop(0)))
        for inside, rel in sorted(entry.include.items()):
            if inside in merged:
                raise CatalogError(f"skill '{entry.name}': include '{inside}' is already a file")
            merged[inside] = (kit_root / rel).read_bytes()
    for root in layers:
        for rel, data in _layer(root):
            if rel.endswith(APPEND):
                target = rel[: -len(APPEND)]
                if target not in merged:
                    raise CatalogError(
                        f"{root.relative_to(kit_root).as_posix()}/{rel}: nothing below to append to"
                    )
                base = merged[target]
                sep = b"" if base.endswith(b"\n") else b"\n"
                merged[target] = base + sep + data
            else:
                merged[rel] = data
    if "SKILL.md" not in merged:
        raise CatalogError(f"skill '{entry.name}' has no SKILL.md for {agent}")
    return sorted(merged.items(), key=lambda item: path_order(item[0]))  # same order as legacy


class SkillSource:
    """name -> merged files for one agent and policy (cached per run), plus static checks.

    kit.plan and kit.verify call it like a function; kit.verify also uses `validate`.
    """

    def __init__(self, kit_root: Path, agent: str, policy: str):
        self.kit_root = kit_root
        self.agent = agent
        self.policy = policy
        self.entries = load(kit_root, policy)
        self.renames = renames(self.entries, agent, policy)
        self.planned: Optional[set] = None  # skills installed together (set by the planner)
        self._cache: Dict[str, List[Tuple[str, bytes]]] = {}
        self._lock = None

    def __call__(self, name: str) -> List[Tuple[str, bytes]]:
        if name not in self._cache:
            entry = self.entries[name]
            files = skill_files(self.kit_root, entry, self.agent, self.policy)
            if entry.origin == "kit":  # follow-up A: no mention of a skill that is not there
                files = rename_mentions(files, self.renames)
            self._cache[name] = files
        return self._cache[name]

    def vendored_files(self, name: str) -> List[str]:
        """Kit-relative third_party/ files this skill is built from (checked against the lock)."""
        entry = self.entries[name]
        rels = []
        if entry.location is not None and entry.location.startswith(THIRD_PARTY + "/"):
            root = self.kit_root / entry.location
            rels += [
                p.relative_to(self.kit_root).as_posix()
                for p in sorted(root.rglob("*"), key=path_order)
                if p.is_file()
            ]
        rels += [rel for rel in entry.include.values() if rel.startswith(THIRD_PARTY + "/")]
        return rels

    def _sibling(self, name: str):
        requires = self.entries[name].requires

        def installed_with(other: str, path: str) -> bool:
            if other not in requires or other not in self.entries:
                return False
            if self.planned is not None and other not in self.planned:
                return False
            return path in dict(self(other))

        return installed_with

    def check(self, name: str):
        from . import skill_check, sources

        entry = self.entries[name]
        kit_rules = entry.origin == "kit"
        report = skill_check.check(name, self(name), self.agent, kit_rules, self._sibling(name))
        vendored = self.vendored_files(name)
        if vendored:
            if self._lock is None:
                self._lock = sources.load(self.kit_root)
            report.errors += sources.check_files(self.kit_root, vendored, self._lock)
        if self.planned is not None:
            missing = [r for r in entry.requires if r not in self.planned]
            if missing:
                report.errors.append(
                    f"needs {', '.join(missing)} installed with it (catalog 'requires')"
                )
        return report

    def validate(self, skill_dir: Path) -> List[str]:
        """Errors for an installed skill folder (used by verify)."""
        from . import skill_check

        files = [
            (p.relative_to(skill_dir).as_posix(), p.read_bytes())
            for p in sorted(skill_dir.rglob("*"), key=path_order)
            if p.is_file() and not is_build_artifact(p.relative_to(skill_dir))
        ]
        name = skill_dir.name
        kit_rules = name not in self.entries or self.entries[name].origin == "kit"
        requires = self.entries[name].requires if name in self.entries else []

        def on_disk(other: str, path: str) -> bool:
            return other in requires and (skill_dir.parent / other / path).is_file()

        return skill_check.check(name, files, self.agent, kit_rules, on_disk).errors


def source_for(kit_root: Path, agent: str, policy: str) -> SkillSource:
    return SkillSource(kit_root, agent, policy)
