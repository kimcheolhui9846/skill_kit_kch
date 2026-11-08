"""Minimal SKILL.md frontmatter parsing and validation (no YAML dependency)."""

from __future__ import annotations

from pathlib import Path

from .skill_check import block_header, fold_plain, is_entry, read_block

MAX_DESCRIPTION = 400


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat `key: value` block between the leading `---` lines. A top-level value may
    be a block scalar (`key: >`, `|-`, ...) or continue on more-indented lines (kit.skill_check
    has the same rules)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    data: dict[str, str] = {}
    current = None
    raw = None  # the top-level value as written, while more lines may continue it
    plain: list = []
    blanks = 0  # blank lines right after the first line of a value
    index = 1
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.strip() == "---":
            _end_plain(data, current, plain)
            return data
        if not line.strip():
            if plain:
                plain.append("")
            blanks += 1
            continue
        if line.lstrip().startswith("#"):
            continue
        skipped, blanks = blanks, 0
        item = line.strip()
        if line[0] in " \t" and (plain or (raw is not None and not is_entry(item))):
            if not plain:
                plain += [raw] + [""] * skipped
            plain.append(item)
            continue
        _end_plain(data, current, plain)
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        current, raw = key.strip(), None
        header = block_header(value) if line[0] not in " \t" else None
        if header is not None:
            data[current], index = read_block(lines, index, header)
            continue
        if line[0] not in " \t":
            raw = value.strip()
        data[current] = _unquote(value)
    raise ValueError("missing closing '---'")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _end_plain(data: dict, key, plain: list) -> None:
    if plain and key is not None:
        data[key] = _unquote(fold_plain(plain))
    plain.clear()


def validate_skill(skill_dir: Path) -> list[str]:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{name}: SKILL.md missing"]
    try:
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return [f"{name}: {exc}"]
    errors = []
    if meta.get("name") != name:
        errors.append(f"{name}: frontmatter name '{meta.get('name')}' does not match folder")
    description = meta.get("description", "")
    if not description:
        errors.append(f"{name}: description missing")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{name}: description too long ({len(description)} > {MAX_DESCRIPTION})")
    elif "Do NOT use" not in description:
        errors.append(f"{name}: description must say when 'Do NOT use' the skill")
    return errors
