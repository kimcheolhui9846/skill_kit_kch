"""`kit source add|list|check|update|remove` (P4-T8, REQ-SRC-009, ADR-021).

Pipeline for one GitHub address:

    resolve -> pin -> fetch -> detect -> license -> scan -> validate -> overlap -> plan
            -> [approval] -> apply -> verify -> record

- resolve/pin/fetch use the GitHub REST API and codeload with urllib (R-08). The ref becomes a
  40-character commit SHA. GITHUB_TOKEN is sent to api.github.com when set; it is never printed.
- The tarball is unpacked in memory only. Nothing from it is executed or written before the
  approval. Paths that escape and special files stop the add; links stop it only when they lie
  inside a chosen skill folder. An archive over MAX_BYTES, packed or unpacked, is fetched
  folder by folder when --path names the folders (the kept bytes are still capped at MAX_BYTES).
- License table (D-09): MIT, Apache-2.0, BSD-2/3, ISC, 0BSD, CC-BY-4.0 and Unlicense are copied
  (vendored-verbatim) into third_party/<owner>-<repo>/<repo path>. Anything else, or no license,
  is recorded as `referenced` (no files). `other` is copied only with --accept-license. Each
  skill keeps the license file nearest to its folder; one source records one license, so
  folders whose licenses differ are recorded as referenced.
- Siblings: a link to `../<skill>/...` is allowed when that skill is chosen in the same run; the
  catalog entry then `requires` it. Two chosen folders with one skill name block the add.
- Scan: secrets in a token format and binary files block (exit 1). Remote-execution one-liners,
  hidden Unicode, prompt-injection phrases and literal values next to a secret name or in a
  Bearer header (the rule set `kit capture` uses, kit.secrets_scan) need a person (exit 2)
  unless --accept-risk. Placeholders such as `<your-token>` and user paths only warn.
- Validate: the official skill limits only (kit.skill_check with kit_rules=False, R-7).
- Overlap (D-20): a name the catalog already has needs a person (verbatim files cannot be
  renamed) and is always listed as an overlap. Token Jaccard similarity >= threshold needs
  --replaces NAME or --keep-both.
- Apply writes third_party files, sources.lock.json, catalog/skills.json (policies: standard
  only, so the restricted path and the .agents/skills mirror never change), THIRD_PARTY_NOTICES.md
  and a row in docs/v2/07_SOURCES_EVALUATION.md. Any failure, including the final
  `sources.check`, puts every file back.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import tarfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Optional, Tuple

from . import catalog, skill_check, sources
from .fsops import path_order, safe_path
from .github_fetch import MAX_BYTES, DownloadTooLarge, GitHub, unquote
from .model import TargetError, UsageError
from .source_scan import Finding, scan_file

THRESHOLD = 0.5
AGENTS = ["codex", "claude"]
CATALOG_REL = catalog.CATALOG_REL
EVAL_REL = "docs/v2/07_SOURCES_EVALUATION.md"
EVAL_HEADING = "## 9. `kit source` 기록"
ADDED_BY = "source add"
ALLOWED = (
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "0BSD",
    "CC-BY-4.0",
    "Unlicense",
)
SCRIPT_EXT = {
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".bat", ".cmd", ".py", ".js", ".mjs",
    ".cjs", ".ts", ".rb", ".pl", ".php", ".exe", ".dll", ".so", ".dylib",
}  # fmt: skip
LICENSE_NAMES = re.compile(r"^(?:LICEN[CS]E|COPYING)(?:[.-][A-Za-z0-9]+)?(?:\.(?:md|txt))?$", re.I)
_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
_REPO = r"[A-Za-z0-9_.-]+"
_SHORT = re.compile(rf"^({_OWNER})/({_REPO})$")
_URL = re.compile(
    rf"^https://(?:www\.)?github\.com/({_OWNER})/({_REPO})(?:/(tree)/([^/]+)(/.*)?)?/?$"
)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = set(
    "the and for with that this you your are use when from not into will can its any all have "
    "has was but then than them they what which while each also only more most such skill "
    "skills file files code".split()
)


@dataclass
class Spec:
    owner: str
    repo: str
    ref: Optional[str] = None
    paths: List[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"


def _clean_path(raw: str) -> str:
    path = raw.strip().strip("/")
    if path.endswith("SKILL.md"):
        path = path[: -len("SKILL.md")].rstrip("/")
    parts = PurePosixPath(path).parts if path else ()
    if "\\" in raw or any(p in ("..", ".") for p in parts):
        raise UsageError(f"bad path '{raw}'")
    return path


def parse_url(text: str, ref: Optional[str] = None, paths: Optional[List[str]] = None) -> Spec:
    """`owner/repo`, `https://github.com/o/r[.git]` or `.../tree/<ref>[/<path>]` (64 otherwise).
    In the tree form the first segment after tree/ is the ref (refs with "/" need --ref)."""
    raw = text.strip()
    if raw.endswith(".git"):
        raw = raw[:-4]
    paths = [_clean_path(p) for p in (paths or [])]
    short = _SHORT.match(raw)
    if short:
        return Spec(short.group(1), short.group(2), ref, paths)
    match = _URL.match(raw)
    if not match:
        raise UsageError(
            f"not a GitHub repository address: '{text}' "
            "(use owner/repo, https://github.com/owner/repo or .../tree/<ref>/<path>)"
        )
    owner, repo, tree, url_ref, url_path = match.groups()
    if tree:
        if ref and ref != url_ref:
            raise UsageError(f"--ref {ref} differs from the ref in the address ({url_ref})")
        ref = ref or unquote(url_ref)
        if url_path and url_path.strip("/"):
            paths = paths + [_clean_path(unquote(url_path))]
    return Spec(owner, repo, ref, paths)


def make_client() -> GitHub:
    """Tests replace this with an offline fake."""
    return GitHub(os.environ.get("GITHUB_TOKEN") or None)


# ---------------------------------------------------------------- unpack (in memory)


class SourceBlocked(Exception):
    """A security or format check stops the add (exit 1)."""


class ArchiveTooLarge(SourceBlocked):
    """The unpacked archive is over the limit; with --path the add fetches folder by folder."""


@dataclass
class Archive:
    files: Dict[str, bytes]  # repo-relative path -> bytes
    links: List[str]  # repo-relative paths of links (never followed)


def _size(limit: int) -> str:
    return f"{limit // (1024 * 1024)} MiB" if limit >= 1024 * 1024 else f"{limit} bytes"


def _escapes(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return (
        name.startswith(("/", "\\"))
        or any(":" in part for part in parts)
        or "\\" in name
        or ".." in parts
    )


def sparse(client, owner: str, repo: str, sha: str, paths: List[str], limit: int = MAX_BYTES):
    """Only the --path folders and the license files above them, one blob at a time.

    Used when the whole-repository archive is over MAX_BYTES (U-40: a 460 MB repository).
    Same rules as unpack: escaping paths and special entries (submodules) stop the add, links
    are recorded, and the selected bytes are capped at `limit`.
    """
    files: Dict[str, bytes] = {}
    links: List[str] = []
    total = 0
    ancestors = {""}
    for path in paths:
        parts = PurePosixPath(path).parts
        ancestors.update("/".join(parts[:i]) for i in range(len(parts)))
    for entry in client.tree(owner, repo, sha):
        rel = entry.get("path")
        if not isinstance(rel, str) or _escapes(rel):
            raise SourceBlocked(f"repository path escapes the folder: {rel}")
        pure = PurePosixPath(rel)
        parent = str(pure.parent) if "/" in rel else ""
        wanted = any(_under(rel, p) for p in paths)
        license_above = parent in ancestors and LICENSE_NAMES.match(pure.name)
        if not (wanted or license_above) or entry.get("type") == "tree":
            continue
        if entry.get("mode") == "120000":
            links.append(rel)
            continue
        if entry.get("type") != "blob":
            raise SourceBlocked(f"special entry in the repository ({entry.get('type')}): {rel}")
        total += int(entry.get("size") or 0)
        if total > limit:
            raise SourceBlocked(f"selected files are larger than {_size(limit)}")
        data = client.blob(owner, repo, entry["sha"], limit)
        if len(data) != int(entry.get("size") or 0):
            raise SourceBlocked(f"GitHub returned a different size for {rel}")
        files[rel] = data
    return Archive(files, links)


def unpack(data: bytes, limit: int = MAX_BYTES) -> Archive:
    files: Dict[str, bytes] = {}
    links: List[str] = []
    total = 0
    cap = limit + 1024 * 1024  # tar headers and padding on top of the file bytes
    try:
        if data[:2] == b"\x1f\x8b":  # read at most cap + 1 bytes (no gzip bomb)
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                raw = stream.read(cap + 1)
        else:
            raw = data
    except (OSError, EOFError) as exc:
        raise SourceBlocked(f"archive is not a gzip file: {exc}") from None
    if len(raw) > cap:
        raise ArchiveTooLarge(f"archive is larger than {_size(limit)}")
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
            for member in tar:
                name = member.name
                parts = PurePosixPath(name).parts
                if _escapes(name):
                    raise SourceBlocked(f"archive path escapes the folder: {name}")
                rel = "/".join(parts[1:])  # drop <repo>-<sha>/
                if member.isdir():
                    continue
                if member.issym() or member.islnk():
                    links.append(rel)
                    continue
                if not member.isfile():
                    raise SourceBlocked(f"special file in the archive: {name}")
                total += member.size
                if total > limit:
                    raise ArchiveTooLarge(f"archive is larger than {_size(limit)}")
                if not rel:
                    continue
                handle = tar.extractfile(member)
                files[rel] = handle.read() if handle else b""
    except tarfile.TarError as exc:
        raise SourceBlocked(f"archive is not a tar file: {exc}") from None
    return Archive(files, links)


# ---------------------------------------------------------------- detect, license, scan


def _under(rel: str, folder: str) -> bool:
    return not folder or rel == folder or rel.startswith(folder + "/")


def find_skills(archive: Archive, paths: List[str]) -> List[str]:
    """Repo folders holding a SKILL.md ("" = repo root), limited to --path when given."""
    found = sorted(
        str(PurePosixPath(rel).parent) if "/" in rel else ""
        for rel in archive.files
        if PurePosixPath(rel).name == "SKILL.md"
    )
    if paths:
        found = [d for d in found if any(_under(d, p) for p in paths)]
    return found


# An MCP server is shown by its manifest or code (an SDK dependency or import), not by a README
# that mentions "mcpServers": agent collections often show how to set up someone else's server.
_MCP_SERVER = re.compile(
    r"@modelcontextprotocol/sdk|modelcontextprotocol/go-sdk|mark3labs/mcp-go|\brmcp\b"
    r"|\bFastMCP\b|\bMcpServer\b|^\s*(?:from|import)\s+(?:mcp|fastmcp)\b"
    r"|^\s*[\"']?(?:mcp|fastmcp)(?:\[[^\]]*\])?\s*(?:[<>=~!]=|[\"'],?\s*$|$)",
    re.M,
)
_MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "go.mod",
    "cargo.toml",
}
_SERVER_CODE = {".py", ".ts", ".mts", ".js", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".cs"}


def detect_kind(archive: Archive, paths: List[str]) -> Optional[str]:
    """For a repo with no skill: plugin, mcp, or None (cannot tell)."""
    inside = [r for r in archive.files if not paths or any(_under(r, p) for p in paths)]
    names = {PurePosixPath(r).as_posix() for r in inside}
    if any(r.endswith(".claude-plugin/plugin.json") or r == "plugin.json" for r in names):
        return "plugin"
    for rel in sorted(inside):
        pure = PurePosixPath(rel.lower())
        if pure.name in _MANIFESTS or pure.suffix in _SERVER_CODE:
            text = archive.files[rel].decode("utf-8", "replace")
            if _MCP_SERVER.search(text):
                return "mcp"
    return None


def _mentions_mcp(archive: Archive, paths: List[str]) -> bool:
    return any(
        PurePosixPath(rel.lower()).name == "readme.md"
        and b"mcpServers" in data
        and (not paths or any(_under(rel, p) for p in paths))
        for rel, data in archive.files.items()
    )


def license_from_text(text: str) -> str:
    t = " ".join(text.split())
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in t:
        return "AGPL-3.0"
    if "GNU LESSER GENERAL PUBLIC LICENSE" in t:
        return "LGPL"
    if "GNU GENERAL PUBLIC LICENSE" in t:
        return "GPL"
    if "Mozilla Public License" in t:
        return "MPL-2.0"
    if "Apache License" in t and "Version 2.0" in t:
        return "Apache-2.0"
    if "Permission is hereby granted, free of charge" in t:
        return "MIT"
    if "Permission to use, copy, modify, and/or distribute this software for any purpose" in t:
        return "ISC" if "provided that the above copyright notice" in t else "0BSD"
    if "Redistribution and use in source and binary forms" in t:
        return "BSD-3-Clause" if "Neither the name" in t else "BSD-2-Clause"
    if "This is free and unencumbered software released into the public domain" in t:
        return "Unlicense"
    if "Creative Commons Attribution 4.0 International" in t and "ShareAlike" not in t:
        return "CC-BY-4.0"
    return "other"


@dataclass
class License:
    spdx: str  # SPDX id, "other" or "none"
    rel: Optional[str]  # repo-relative license file
    note: str = ""


def find_license(archive: Archive, folder: str, api_spdx: Optional[str]) -> License:
    """The license file nearest to the skill folder (the folder itself, then its parents)."""
    parts = PurePosixPath(folder).parts if folder else ()
    for depth in range(len(parts), -1, -1):
        base = "/".join(parts[:depth])
        names = sorted(
            r
            for r in archive.files
            if (str(PurePosixPath(r).parent) if "/" in r else "") == base
            and LICENSE_NAMES.match(PurePosixPath(r).name)
        )
        if names:
            rel = names[0]
            text = archive.files[rel].decode("utf-8", "replace")
            found = license_from_text(text)
            known_api = api_spdx not in (None, "", "NOASSERTION", "NONE")
            if base == "" and known_api:
                if found == "other":
                    return License(api_spdx, rel, "license text read by GitHub")
                if not api_spdx.startswith(found.split("-")[0]):
                    return License(found, rel, f"GitHub reports {api_spdx}")
            return License(found, rel)
    return License("none", None)


def vendorable(lic: License, accept: bool) -> bool:
    return lic.spdx in ALLOWED or (lic.spdx == "other" and accept)


def _tokens(data: bytes) -> set:
    text = data.decode("utf-8", "replace").lower()
    return {w for w in _WORD.findall(text) if len(w) > 2 and w not in _STOP}


def similarity(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


# ---------------------------------------------------------------- plan


@dataclass
class SkillPick:
    name: str
    folder: str  # repo-relative ("" = root)
    files: Dict[str, bytes]  # repo-relative path -> bytes (taken)
    left_out: List[str]  # repo-relative scripts not taken
    license: License = field(default_factory=lambda: License("none", None))  # nearest to it
    requires: List[str] = field(default_factory=list)  # sibling skills its links reach


@dataclass
class Plan:
    spec: Spec
    commit: str
    ref: str
    source_id: str
    kind: str
    license: License
    vendored: bool
    picks: List[SkillPick] = field(default_factory=list)
    writes: Dict[str, bytes] = field(default_factory=dict)  # kit rel -> bytes (third_party)
    deletes: List[str] = field(default_factory=list)  # kit rel (update/remove)
    entry: dict = field(default_factory=dict)  # sources.lock.json entry
    catalog_entries: List[dict] = field(default_factory=list)
    overlaps: List[dict] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    unchanged: bool = False
    needs: List[str] = field(default_factory=list)  # reasons a person must decide

    @property
    def blocked(self) -> bool:
        return any(f.level == "BLOCK" for f in self.findings)


@dataclass
class Options:
    pack: Optional[str] = None
    all_skills: bool = False
    name: Optional[str] = None
    accept_license: bool = False
    accept_risk: bool = False
    replaces: List[str] = field(default_factory=list)
    keep_both: bool = False
    include: List[str] = field(default_factory=list)
    threshold: float = THRESHOLD


def folder_of(spec: Spec) -> str:
    return f"{spec.owner}-{spec.repo}"


def _slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def _read_json(kit_root: Path, rel: str) -> dict:
    return json.loads((kit_root / rel).read_text(encoding="utf-8"))


def _pack_names(kit_root: Path) -> List[str]:
    from .profile_resolver import list_entries

    return [name for name, _ in list_entries(kit_root)]


def _existing_tokens(kit_root: Path, skip_origin: Optional[str]) -> Dict[str, set]:
    out: Dict[str, set] = {}
    for name, options in catalog.load_all(kit_root).items():
        for entry in options:
            if entry.location is None or entry.origin == skip_origin:
                continue
            path = kit_root / entry.location / "SKILL.md"
            if path.is_file():
                out.setdefault(name, set()).update(_tokens(path.read_bytes()))
    return out


def build(
    kit_root: Path,
    spec: Spec,
    opts: Options,
    client: GitHub,
    previous: Optional[sources.Source] = None,
) -> Plan:
    """Everything up to the plan. Raises SourceBlocked, TargetError, NetworkError."""
    info = client.repo(spec.owner, spec.repo)
    owner, repo = info["full_name"].split("/", 1)
    if (owner, repo) != (spec.owner, spec.repo):
        spec = Spec(owner, repo, spec.ref, spec.paths)
    ref = spec.ref or info["default_branch"]
    commit = ref if _SHA.match(ref) else client.commit(owner, repo, ref)
    origin = f"https://github.com/{owner}/{repo}"
    lock = sources.load(kit_root)

    if previous is None:
        for src in lock.values():
            if "paths" not in src.raw:  # added by hand: same origin and the same folder
                carried = {x.strip().strip("/") for x in str(src.raw.get("path", "")).split(",")}
                if src.origin.lower() == origin.lower() and set(spec.paths) & carried:
                    raise _Needs(
                        f"already carried as '{src.id}' (added by hand at {src.commit[:12]}); "
                        "nothing to add"
                    )
                continue
            same_paths = _paths_of(src) == sorted(spec.paths)
            if src.origin.lower() == origin.lower() and same_paths and src.commit == commit:
                plan = Plan(spec, commit, ref, src.id, src.kind, License(src.license, None), False)
                plan.unchanged = True
                plan.notes.append(f"already in {sources.LOCK_REL} as '{src.id}' at this commit")
                return plan
            if src.origin.lower() == origin.lower() and same_paths:
                raise _Needs(
                    f"already added as '{src.id}' at {src.commit[:12]}; "
                    f"use `kit source update {src.id}` for a new commit"
                )
    elif previous.commit == commit:
        plan = Plan(
            spec, commit, ref, previous.id, previous.kind, License(previous.license, None), False
        )  # noqa: E501
        plan.unchanged = True
        plan.notes.append(f"'{previous.id}' is already at {commit[:12]}")
        return plan

    try:
        archive = unpack(client.tarball(owner, repo, commit))
    except (DownloadTooLarge, ArchiveTooLarge) as exc:  # packed or unpacked over MAX_BYTES
        if not spec.paths:
            raise SourceBlocked(f"{exc}; name the folders with --path") from None
        try:  # a large repository: fetch only the chosen folders
            archive = sparse(client, owner, repo, commit, spec.paths)
        except DownloadTooLarge as inner:
            raise SourceBlocked(str(inner)) from None
    if spec.paths:
        for path in spec.paths:
            if not any(_under(r, path) for r in archive.files):
                raise TargetError(f"path '{path}' not found in {owner}/{repo}@{commit[:12]}")
    folders = find_skills(archive, spec.paths)
    plan_kind = "skill"
    if not folders:
        kind = detect_kind(archive, spec.paths)
        if kind is None:
            raise _Needs(
                f"no SKILL.md, plugin.json or MCP server found in {owner}/{repo}"
                + (f" under {', '.join(spec.paths)}" if spec.paths else "")
                + (
                    " (the README mentions mcpServers, but there is no server code or "
                    "MCP SDK dependency)"
                    if _mentions_mcp(archive, spec.paths)
                    else ""
                )
            )
        plan_kind = kind
    elif len(folders) > 1 and not opts.all_skills and not spec.paths and previous is None:
        listing = ", ".join(f or "(root)" for f in folders)
        raise _Needs(
            f"{len(folders)} skills found: {listing}. Pick with --path (repeatable; a folder "
            "takes every skill under it) or --all"
        )  # noqa: E501
    if len(folders) > 1:
        plan_kind = "skill-bundle"

    licenses = {f: find_license(archive, f, info["spdx"]) for f in folders}
    lic, mixed = _overall_license(archive, folders, licenses, info["spdx"], opts.accept_license)
    vendored = (
        plan_kind in ("skill", "skill-bundle")
        and not mixed
        and vendorable(lic, opts.accept_license)
    )
    source_id = previous.id if previous else _choose_id(lock, spec, folders, opts.name, archive)
    plan = Plan(spec, commit, ref, source_id, plan_kind, lic, vendored)
    if info["archived"]:
        plan.findings.append(Finding("WARN", f"{owner}/{repo} is archived (no more updates)"))
    if opts.accept_license and lic.spdx != "other":
        plan.notes.append(f"--accept-license has no effect on {lic.spdx} (only on 'other')")
    if lic.note:
        plan.notes.append(f"license: {lic.note}")
    if mixed:
        listing = ", ".join(f"{f or '/'}: {licenses[f].spdx}" for f in folders)
        plan.notes.append(
            f"the chosen folders have different licenses ({listing}); one source records one "
            "license, so it is recorded as referenced. Add the folders with the same license "
            "in one run and the others separately."
        )
    elif plan_kind in ("skill", "skill-bundle") and not vendored:
        plan.notes.append(
            f"license {lic.spdx} is not on the copy list: recorded as referenced, no files copied"
        )
    if plan_kind in ("plugin", "mcp"):
        plan.notes.append(
            f"{plan_kind}: recorded as referenced; add a pinned catalog/{'plugins' if plan_kind == 'plugin' else 'mcp'}.json entry by hand"  # noqa: E501
        )

    base = f"{sources.THIRD_PARTY}/{folder_of(spec)}"
    if vendored:
        includes = {_clean_path(i) for i in opts.include}
        for folder in folders:
            for link in archive.links:
                if _under(link, folder):
                    raise SourceBlocked(f"link inside the skill folder: {link}")
            name = PurePosixPath(folder).name if folder else _root_name(archive, repo)
            taken, left = {}, []
            for rel, data in sorted(archive.files.items()):
                if not _under(rel, folder):
                    continue
                if PurePosixPath(rel).suffix.lower() in SCRIPT_EXT and rel not in includes:
                    left.append(rel)
                    continue
                taken[rel] = data
            own = licenses[folder]
            plan.picks.append(SkillPick(name, folder, taken, left, own))
            declared = _declared_license(archive, folder)
            if declared and not declared.lower().startswith(own.spdx.lower()):
                plan.notes.append(
                    f"{name}: SKILL.md says 'license: {declared}'; "
                    f"the license file found is {own.spdx} ({own.rel or 'none'})"
                )
        _same_names(plan)
        unknown = includes - {r for p in plan.picks for r in p.files}
        if unknown:
            raise UsageError(
                f"--include path not in the chosen skills: {', '.join(sorted(unknown))}"
            )  # noqa: E501
        for pick in plan.picks:
            for rel, data in pick.files.items():
                plan.writes[f"{base}/{rel}"] = data
        for pick in plan.picks:  # each skill's own license file (D-09)
            if pick.license.rel:
                plan.writes[f"{base}/{pick.license.rel}"] = archive.files[pick.license.rel]
        for rel, data in sorted(plan.writes.items()):
            plan.findings += scan_file(rel, data)
        _validate(plan, archive)
        _overlap(kit_root, plan, opts, previous)
        _clashes(kit_root, plan, lock, previous)
    _entries(kit_root, plan, opts, previous, base)
    if any(f.level == "REVIEW" for f in plan.findings) and not opts.accept_risk:
        plan.needs.append("scan findings need a person (re-run with --accept-risk after review)")
    return plan


def _declared_license(archive: Archive, folder: str) -> Optional[str]:
    """The SKILL.md frontmatter `license` text, shown when it differs from the license file."""
    rel = f"{folder}/SKILL.md" if folder else "SKILL.md"
    try:
        meta = skill_check.parse_frontmatter(archive.files[rel].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, ValueError):
        return None
    value = meta.get("license")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _root_name(archive: Archive, repo: str) -> str:
    """A skill at the repo root installs under its frontmatter name."""
    try:
        meta = skill_check.parse_frontmatter(archive.files["SKILL.md"].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _slug(repo)
    name = meta.get("name")
    return name if isinstance(name, str) and name else _slug(repo)


def _overall_license(
    archive: Archive,
    folders: List[str],
    licenses: Dict[str, License],
    api_spdx: Optional[str],
    accept: bool,
) -> Tuple[License, bool]:
    """The source's one license from each folder's own (nearest) license, and whether they
    disagree. Folders with the same license may keep different license files (each skill gets
    its own); one source cannot record two licenses, nor copy some folders and not others."""
    if not folders:
        return find_license(archive, "", api_spdx), False
    found = [licenses[f] for f in folders]
    kinds = {(lic.spdx, vendorable(lic, accept)) for lic in found}
    if len(kinds) > 1:
        return find_license(archive, _common(folders), api_spdx), True
    rels = [lic.rel for lic in found]
    primary = min(set(rels), key=lambda r: (-rels.count(r), r or ""))
    note = next((lic.note for lic in found if lic.rel == primary and lic.note), "")
    return License(found[0].spdx, primary, note), False


def _same_names(plan: Plan) -> None:
    """Two chosen folders that install under one name (e.g. skills/x and .openclaw/skills/x)."""
    seen: Dict[str, str] = {}
    for pick in plan.picks:
        if pick.name in seen:
            plan.findings.append(
                Finding(
                    "BLOCK",
                    f"two skills are named '{pick.name}': {seen[pick.name] or '/'} and "
                    f"{pick.folder or '/'}; pick one with --path",
                )
            )
        else:
            seen[pick.name] = pick.folder


class _Needs(Exception):
    """A person must decide (exit 2)."""


def _common(folders: List[str]) -> str:
    parts = [PurePosixPath(f).parts for f in folders]
    out = []
    for group in zip(*parts):
        if len(set(group)) != 1:
            break
        out.append(group[0])
    return "/".join(out)


def _paths_of(src: sources.Source) -> List[str]:
    raw = src.raw.get("paths")
    return sorted(raw) if isinstance(raw, list) else []


def _choose_id(lock, spec: Spec, folders: List[str], name: Optional[str], archive: Archive) -> str:
    if name:
        if not sources._ID.match(name):
            raise UsageError("--name must use a-z, 0-9 and single hyphens")
        if name in lock:
            raise _Needs(f"source id '{name}' is already used; pick another --name")
        return name
    if len(folders) == 1:
        first = folders[0]
        base = _slug(PurePosixPath(first).name if first else _root_name(archive, spec.repo))
        for candidate in (base, _slug(f"{spec.owner}-{base}")):
            if candidate not in lock:
                return candidate
    candidate = _slug(f"{spec.owner}-{spec.repo}")
    if candidate in lock:
        raise _Needs(f"source id '{candidate}' is already used; pass --name")
    return candidate


_OUTSIDE = re.compile(r"^(?P<rel>.+): link '(?P<link>[^']*)' points outside the skill$")


def _installed_files(pick: SkillPick) -> List[Tuple[str, bytes]]:
    """The skill's files as installed: paths inside its folder, plus its license file."""
    files = [
        (PurePosixPath(rel).relative_to(pick.folder).as_posix() if pick.folder else rel, data)
        for rel, data in pick.files.items()
    ]
    if pick.license.rel and not _under(pick.license.rel, pick.folder):
        files.append(("LICENSE", b"license"))  # the catalog includes it next to the skill
    return files


def _validate(plan: Plan, archive: Archive) -> None:
    """Official limits only. A link to `../<sibling>/<file>` is allowed when that sibling is
    chosen in the same run: the catalog entry then `requires` it, so they install together."""
    installed: Dict[str, set] = {}
    for pick in plan.picks:
        installed.setdefault(pick.name, {rel for rel, _ in _installed_files(pick)})
    for pick in plan.picks:
        files = _installed_files(pick)
        used: set = set()

        def sibling(other: str, path: str, me: str = pick.name, used: set = used) -> bool:
            if other != me and path in installed.get(other, ()):
                used.add(other)
                return True
            return False

        for agent in AGENTS:
            report = skill_check.check(pick.name, files, agent, kit_rules=False, sibling=sibling)
            plan.findings += [
                Finding("BLOCK", f"{pick.name} ({agent}): {_hint(e, pick, archive)}")
                for e in report.errors
            ]
            plan.findings += [
                Finding("WARN", f"{pick.name} ({agent}): {w}") for w in report.warnings
            ]
        pick.requires = sorted(used)


def _hint(error: str, pick: SkillPick, archive: Archive) -> str:
    """For a link into a sibling skill that is not chosen: name the --path that takes it."""
    match = _OUTSIDE.match(error)
    if not match or not pick.folder:
        return error
    target = match.group("link").split("#", 1)[0]
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(match.group("rel")), target))
    parts = joined.split("/", 2)
    if len(parts) < 3 or parts[0] != "..":
        return error
    parent = str(PurePosixPath(pick.folder).parent) if "/" in pick.folder else ""
    folder = f"{parent}/{parts[1]}" if parent else parts[1]
    if f"{folder}/SKILL.md" not in archive.files:
        return error
    return f"{error}; it is the skill in {folder}: add --path {folder} to take both"


def _overlap(kit_root: Path, plan: Plan, opts: Options, previous) -> None:
    if previous is not None:  # decided at add time; kept as recorded
        plan.overlaps = list(previous.raw.get("overlap", []))
        return
    existing = _existing_tokens(kit_root, None)
    names = set(catalog.load_all(kit_root))
    for bad in opts.replaces:
        if bad not in names:
            raise UsageError(f"--replaces: unknown skill '{bad}'")
    for pick in plan.picks:
        mine = _tokens(pick.files[f"{pick.folder}/SKILL.md" if pick.folder else "SKILL.md"])
        for other in sorted(set(existing) | ({pick.name} & names)):
            score = round(similarity(mine, existing.get(other, set())), 2)
            same_name = other == pick.name  # always an overlap, whatever the words say
            if score < opts.threshold and not same_name:
                continue
            if other in opts.replaces:
                decision = "replace-in-standard"
            elif opts.keep_both:
                decision = "keep-both"
            else:
                decision = None
            if decision is None and not same_name:  # a same name is asked about in _clashes
                plan.needs.append(
                    f"{pick.name} overlaps {other} (similarity {score}); "
                    f"re-run with --replaces {other} or --keep-both"
                )
            plan.overlaps.append(
                {"skill": pick.name, "with": other, "score": score, "decision": decision}
            )  # noqa: E501
    for bad in opts.replaces:
        if not any(o["with"] == bad for o in plan.overlaps):
            plan.overlaps.append(
                {
                    "skill": plan.picks[0].name if plan.picks else "",
                    "with": bad,
                    "score": None,
                    "decision": "replace-in-standard",
                }
            )  # noqa: E501


def _clashes(kit_root: Path, plan: Plan, lock, previous) -> None:
    mine = f"source:{previous.id}" if previous else None
    for name, options in catalog.load_all(kit_root).items():
        for pick in plan.picks:
            if pick.name == name and any(e.origin != mine for e in options):
                plan.needs.append(
                    f"catalog already has a skill named '{name}'; vendored files keep their "
                    "name, so pick a different --path or remove the other skill first"
                )
    own = set(previous.files) if previous else set()
    for rel, data in plan.writes.items():
        path = kit_root / rel
        if path.is_file() and path.read_bytes() != data and rel not in own:
            plan.findings.append(Finding("BLOCK", f"{rel} already exists with different content"))


def _entries(kit_root: Path, plan: Plan, opts: Options, previous, base: str) -> None:
    spec = plan.spec
    today = date.today().isoformat()
    files = {rel: hashlib.sha256(data).hexdigest() for rel, data in sorted(plan.writes.items())}  # noqa: E501
    packs = list(previous.raw.get("packs", [])) if previous else ([opts.pack] if opts.pack else [])
    risk = "medium" if any(f.level in ("REVIEW", "WARN") for f in plan.findings) else "low"
    entry = {
        "id": plan.source_id,
        "kind": plan.kind,
        "origin": f"https://github.com/{spec.owner}/{spec.repo}",
        "path": ", ".join(p.folder or "/" for p in plan.picks) or ", ".join(spec.paths) or "/",
        "paths": sorted(spec.paths),
        "ref": plan.ref,
        "commit": plan.commit,
        "version": None,
        "license": plan.license.spdx,
        "integration": "vendored-verbatim" if plan.vendored else "referenced",
        "local_paths": sorted({f"{base}/{p.folder}".rstrip("/") for p in plan.picks})
        if plan.vendored
        else [],  # noqa: E501
        "files": files,
        "content_sha256": sources.digest(files),
        "agents": list(AGENTS),
        "scope": ["project"],
        "packs": packs,
        "risk": risk,
        "added": previous.raw.get("added") if previous else today,
        "added_by": ADDED_BY,
        "overlap": plan.overlaps,
        "verification": {
            "status": "verified" if plan.vendored else "referenced",
            "by": "kit source " + ("update" if previous else "add"),
            "at": today,
            "notes": "Fetched from codeload at the pinned commit and unpacked in memory; nothing "
            "was executed."
            + (
                " Accepted after review: scan findings (--accept-risk)."
                if opts.accept_risk and any(f.level == "REVIEW" for f in plan.findings)
                else ""
            )  # noqa: E501
            + (
                " License 'other' accepted (--accept-license)."
                if plan.vendored and plan.license.spdx == "other"
                else ""
            ),  # noqa: E501
        },
    }
    if plan.vendored:
        entry["license_file"] = f"{base}/{plan.license.rel}" if plan.license.rel else None
        if not plan.license.rel or any(not p.license.rel for p in plan.picks):
            plan.findings.append(Finding("BLOCK", "no license file to keep next to the files"))
    plan.entry = entry
    if plan.vendored:
        for pick in plan.picks:
            item = {
                "name": pick.name,
                "location": f"{base}/{pick.folder}".rstrip("/"),
                "origin": f"source:{plan.source_id}",
                "agents": list(AGENTS),
                "packs": packs,
                "policies": ["standard"],
            }
            if pick.license.rel and not _under(pick.license.rel, pick.folder):
                item["include"] = {"LICENSE": f"{base}/{pick.license.rel}"}
            mine = sorted(
                {
                    o["with"]
                    for o in plan.overlaps
                    if o.get("skill") == pick.name and o.get("decision") == "replace-in-standard"
                }
            )
            if mine:
                item["replaces"] = mine
            if pick.requires:  # its links reach these sibling skills (installed together)
                item["requires"] = list(pick.requires)
            plan.catalog_entries.append(item)
    if previous is not None:
        plan.deletes = sorted(set(previous.files) - set(files) - _shared(kit_root, previous.id))
    if opts.pack and opts.pack not in _pack_names(kit_root):
        raise UsageError(f"--pack: unknown profile or pack '{opts.pack}'")
    if plan.vendored and not packs:
        plan.notes.append("no --pack: the skill is in the catalog but no profile installs it yet")


def _shared(kit_root: Path, source_id: str) -> set:
    """Files other lock entries also list (e.g. a repo-root LICENSE)."""
    lock = sources.load(kit_root)
    return {rel for s in lock.values() if s.id != source_id for rel in s.files}


# ---------------------------------------------------------------- apply (atomic)


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".kit-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class _Txn:
    def __init__(self, kit_root: Path):
        self.root = kit_root
        self.saved: Dict[str, Optional[bytes]] = {}

    def _save(self, rel: str) -> None:
        if rel not in self.saved:
            path = safe_path(self.root, rel)  # P6-T3: refused before any write
            self.saved[rel] = path.read_bytes() if path.is_file() else None

    def write(self, rel: str, data: bytes) -> None:
        self._save(rel)
        _write_file(safe_path(self.root, rel), data)

    def delete(self, rel: str) -> None:
        self._save(rel)
        path = safe_path(self.root, rel)
        if path.is_file():
            path.unlink()
            _prune(path.parent, self.root / sources.THIRD_PARTY)

    def rollback(self) -> None:
        for rel, data in self.saved.items():
            path = self.root / rel
            if data is None:
                if path.is_file():
                    path.unlink()
                    _prune(path.parent, self.root / sources.THIRD_PARTY)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            tmp = path.with_name(path.name + ".kit-tmp")
            if tmp.is_file():
                tmp.unlink()


def _prune(folder: Path, stop: Path) -> None:
    while (
        folder != stop and stop in folder.parents and folder.is_dir() and not any(folder.iterdir())
    ):  # noqa: E501
        folder.rmdir()
        folder = folder.parent


def _dump(data: dict, original: bytes = b"\n") -> bytes:
    """Same style as the file it replaces: \\u escapes and the final newline."""
    ascii_only = b"\\u" in original
    end = "\n" if original.endswith(b"\n") else ""
    return (json.dumps(data, indent=2, ensure_ascii=ascii_only) + end).encode("utf-8")


def _load(kit_root: Path, rel: str) -> Tuple[dict, bytes]:
    raw = (kit_root / rel).read_bytes()
    return json.loads(raw.decode("utf-8")), raw


def _notice_block(plan: Plan) -> str:
    spec = plan.spec
    names = ", ".join(p.name for p in plan.picks)
    used = ", ".join(f"`{p.folder or '/'}`" for p in plan.picks)
    base = f"{sources.THIRD_PARTY}/{folder_of(spec)}"
    files = sorted({f"{base}/{p.license.rel}" for p in plan.picks if p.license.rel})
    lic = "`, `".join(files) or plan.entry.get("license_file")
    return (
        f"<!-- kit-source:begin {plan.source_id} -->\n"
        f"### {spec.owner}/{spec.repo} — {names}\n\n"
        f"- Repository: https://github.com/{spec.owner}/{spec.repo}\n"
        f"- Commit: {plan.commit}\n"
        f"- License: {plan.license.spdx}, in `{lic}` (installed with the skill)\n"
        f"- Used verbatim: {used}\n"
        f"- Added by `kit source add` ({plan.entry['added']}).\n"
        f"<!-- kit-source:end {plan.source_id} -->\n"
    )


def _without_block(text: str, source_id: str) -> str:
    pattern = re.compile(
        rf"\n?<!-- kit-source:begin {re.escape(source_id)} -->\n.*?<!-- kit-source:end {re.escape(source_id)} -->\n",  # noqa: E501
        re.S,
    )
    return pattern.sub("", text)


def _eval_row(kit_root: Path, text: str, row: str) -> Optional[str]:
    if EVAL_HEADING not in text:
        text = text.rstrip("\n") + (
            f"\n\n{EVAL_HEADING}\n\n`kit source`가 남기는 기록이다(P4-T8, ADR-021).\n\n"
            "| 날짜 | 동작 | id | 출처@커밋 | 라이선스 | 반영 | 팩 | 겹침 |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
    return text.rstrip("\n") + "\n" + row + "\n"


def _row(action: str, entry: dict) -> str:
    overlap = (
        "; ".join(
            f"{o['with']} {o.get('score')} {o.get('decision')}" for o in entry.get("overlap", [])
        )
        or "—"
    )  # noqa: E501
    origin = entry["origin"].replace("https://github.com/", "")
    return (
        f"| {date.today().isoformat()} | {action} | `{entry['id']}` | {origin}@{entry['commit'][:12]} "  # noqa: E501
        f"| {entry['license']} | {entry['integration']} | {', '.join(entry.get('packs', [])) or '—'} | {overlap} |"  # noqa: E501
    )


def _replaced(entry: dict) -> List[str]:
    return sorted(
        {o["with"] for o in entry.get("overlap", []) if o.get("decision") == "replace-in-standard"}
    )


def _verify(kit_root: Path) -> List[str]:
    problems = sources.check(kit_root)
    try:
        catalog.load_all(kit_root)
    except catalog.CatalogError as exc:
        problems.append(str(exc))
    return problems


def _commit(kit_root: Path, txn: _Txn, writes: Dict[str, bytes], deletes: List[str]) -> List[str]:
    """Write everything, then check; on any failure put every file back."""
    try:
        for rel in deletes:
            txn.delete(rel)
        for rel, data in writes.items():
            txn.write(rel, data)
        problems = _verify(kit_root)
    except Exception as exc:  # any failure: put every file back, report it (exit 1)
        txn.rollback()
        return [f"apply failed: {type(exc).__name__}: {exc}"]
    if problems:
        txn.rollback()
    return problems


def apply(kit_root: Path, plan: Plan, previous: Optional[sources.Source] = None) -> List[str]:
    """[] on success; otherwise the problems, with every file put back."""
    lock, lock_raw = _load(kit_root, sources.LOCK_REL)
    lock["sources"] = [s for s in lock["sources"] if s.get("id") != plan.source_id]
    lock["sources"].append(plan.entry)
    writes: Dict[str, bytes] = dict(plan.writes)
    writes[sources.LOCK_REL] = _dump(lock, lock_raw)
    origin = f"source:{plan.source_id}"
    if plan.vendored or previous is not None:
        cat, cat_raw = _load(kit_root, CATALOG_REL)
        kept = [s for s in cat["skills"] if s.get("origin") != origin]
        if previous is None:  # D-20: the replaced skill leaves the standard policy
            for name in _replaced(plan.entry):
                for item in kept:
                    policies = item.get("policies", ["standard"])
                    if item["name"] == name and "standard" in policies:
                        item["policies"] = [p for p in policies if p != "standard"]
        if previous is not None:
            old = {s["name"]: s for s in cat["skills"] if s.get("origin") == origin}
            for item in plan.catalog_entries:  # keep pack / replaces choices made since
                if item["name"] in old:
                    for key in ("packs", "replaces", "policies", "agents"):
                        if key in old[item["name"]]:
                            item[key] = old[item["name"]][key]
        cat["skills"] = kept + plan.catalog_entries
        writes[CATALOG_REL] = _dump(cat, cat_raw)
    notices_path = kit_root / sources.NOTICES_REL
    notices = notices_path.read_text(encoding="utf-8") if notices_path.is_file() else ""
    notices = _without_block(notices, plan.source_id)
    if plan.vendored:
        notices = notices.rstrip("\n") + "\n\n" + _notice_block(plan)
    writes[sources.NOTICES_REL] = notices.encode("utf-8")
    eval_path = kit_root / EVAL_REL
    if eval_path.is_file():
        action = "update" if previous else "add"
        text = _eval_row(kit_root, eval_path.read_text(encoding="utf-8"), _row(action, plan.entry))
        writes[EVAL_REL] = text.encode("utf-8")
    return _commit(kit_root, _Txn(kit_root), writes, plan.deletes)


# ---------------------------------------------------------------- remove


@dataclass
class Removal:
    source: sources.Source
    deletes: List[str]
    skills: List[str]
    needs: List[str] = field(default_factory=list)


def plan_remove(kit_root: Path, source_id: str) -> Removal:
    lock = sources.load(kit_root)
    if source_id not in lock:
        raise TargetError(f"no source '{source_id}' in {sources.LOCK_REL}")
    src = lock[source_id]
    origin = f"source:{source_id}"
    skills = [
        s["name"] for s in _read_json(kit_root, CATALOG_REL)["skills"] if s.get("origin") == origin
    ]  # noqa: E501
    removal = Removal(src, sorted(set(src.files) - _shared(kit_root, source_id)), skills)
    if src.raw.get("added_by") != ADDED_BY:
        removal.needs.append(
            f"'{source_id}' was not added by `kit source add`; profiles and docs may rely on "
            "it, so remove it by hand"
        )
    for name in _named_in_profiles(kit_root, skills):
        removal.needs.append(f"a profile or pack names '{name}'; take it out there first")
    return removal


def _named_in_profiles(kit_root: Path, skills: List[str]) -> List[str]:
    found = []
    for folder in ("profiles", "profiles/packs"):
        for path in sorted((kit_root / folder).glob("*.json"), key=path_order):
            text = path.read_text(encoding="utf-8")
            found += [s for s in skills if f'"{s}"' in text and s not in found]
    return found


def apply_remove(kit_root: Path, removal: Removal) -> List[str]:
    source_id = removal.source.id
    lock, lock_raw = _load(kit_root, sources.LOCK_REL)
    entry = next(s for s in lock["sources"] if s.get("id") == source_id)
    lock["sources"] = [s for s in lock["sources"] if s.get("id") != source_id]
    cat, cat_raw = _load(kit_root, CATALOG_REL)
    cat["skills"] = [s for s in cat["skills"] if s.get("origin") != f"source:{source_id}"]
    for name in _replaced(entry):  # give the standard policy back
        same = [s for s in cat["skills"] if s["name"] == name]
        if same and not any("standard" in s.get("policies", ["standard"]) for s in same):
            had = set(same[0].get("policies", [])) | {"standard"}
            same[0]["policies"] = [p for p in catalog.POLICIES if p in had]
    writes = {sources.LOCK_REL: _dump(lock, lock_raw), CATALOG_REL: _dump(cat, cat_raw)}
    notices_path = kit_root / sources.NOTICES_REL
    if notices_path.is_file():
        text = notices_path.read_text(encoding="utf-8")
        writes[sources.NOTICES_REL] = _without_block(text, source_id).encode("utf-8")
    eval_path = kit_root / EVAL_REL
    if eval_path.is_file():
        text = _eval_row(kit_root, eval_path.read_text(encoding="utf-8"), _row("remove", entry))
        writes[EVAL_REL] = text.encode("utf-8")
    return _commit(kit_root, _Txn(kit_root), writes, removal.deletes)


# ---------------------------------------------------------------- online check


def check_online(kit_root: Path, client: GitHub) -> List[str]:
    problems = []
    for src in sources.load(kit_root).values():
        owner, repo = src.origin.replace("https://github.com/", "").split("/", 1)
        if not client.commit_exists(owner, repo, src.commit):
            problems.append(f"{src.id}: commit {src.commit[:12]} not found at {src.origin}")
    return problems


Ask = Callable[[str], str]
