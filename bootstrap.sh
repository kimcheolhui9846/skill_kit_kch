#!/usr/bin/env bash
# Entry point for bash. Hands off to the Python core when Python 3.9+ exists;
# otherwise copies AGENTS.md and the skills into the target (shell-only mode).
set -u

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEGIN_MARK='<!-- hackathon-kit:begin -->'
END_MARK='<!-- hackathon-kit:end -->'

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--profile core|python|data|web|full] [--target DIR]
                    [--dry-run] [--offline] [--verify-only] [--no-mcp] [--verbose]

Installs AGENTS.md and the Codex skills into the target workspace
(default: current directory). Python 3.9+ enables verification, tools and MCP;
without Python only AGENTS.md and the skills are copied.

Exit codes:
  0   READY (or dry-run completed)
  1   PARTIAL - required items OK, optional items failed or unsupported
  2   BLOCKED - a required item failed or needs your decision
  64  invalid arguments
  65  target workspace missing or not a directory
EOF
}

python_ok() {
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}

find_python() {
  if [ -n "${KIT_PYTHON+set}" ]; then
    python_ok "$KIT_PYTHON" && printf '%s\n' "$KIT_PYTHON"
    return
  fi
  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && python_ok "$cand"; then
      printf '%s\n' "$cand"
      return 0
    fi
  done
  return 1
}

SUBCOMMANDS=" install plan verify doctor update uninstall restore profiles source capture task req trace report recover help version "
IS_SUBCOMMAND=0
if [ $# -gt 0 ]; then
  case "$SUBCOMMANDS" in
    *" $1 "*) IS_SUBCOMMAND=1 ;;
  esac
fi

if [ "$IS_SUBCOMMAND" -eq 0 ]; then
  for arg in "$@"; do
    case "$arg" in
      -h|--help) usage; exit 0 ;;
    esac
  done
fi

if PY="$(find_python)"; then
  export KIT_SHELL=bash
  exec "$PY" -I "$KIT_ROOT/run_kit.py" "$@"
fi

# ---- shell-only mode -------------------------------------------------------
if [ "$IS_SUBCOMMAND" -eq 1 ]; then
  echo "error: '$1' requires Python 3.9+ (shell-only mode supports only the legacy install)" >&2
  exit 64
fi
TARGET="$PWD"
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)
      [ $# -ge 2 ] || { echo "error: --profile needs a value" >&2; exit 64; }
      case "$2" in
        core|python|data|web|full) ;;
        *) echo "error: unknown profile: $2" >&2; exit 64 ;;
      esac
      shift 2 ;;
    --target)
      [ $# -ge 2 ] || { echo "error: --target needs a value" >&2; exit 64; }
      [ -n "$2" ] || { echo "error: --target needs a non-empty directory" >&2; exit 64; }
      TARGET="$2"
      shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verify-only)
      echo "error: --verify-only requires Python 3.9+ (shell-only mode cannot verify)" >&2
      exit 64 ;;
    --offline|--no-mcp|--verbose) shift ;;
    *)
      echo "error: unknown argument: $1" >&2
      echo "Run with --help for usage." >&2
      exit 64 ;;
  esac
done

if [ ! -d "$TARGET" ]; then
  echo "error: target is not an existing directory: $TARGET" >&2
  exit 65
fi
TARGET="$(cd "$TARGET" && pwd)"
if [ "$TARGET" = "$KIT_ROOT" ]; then
  echo "error: target is the kit folder itself; run from your workspace or pass --target <workspace>" >&2
  exit 65
fi
CONFLICT=0

note() { printf '  %-9s %s\n' "$1" "$2"; }

fail_blocked() {
  echo "error: $1" >&2
  echo "Target:       $TARGET"
  echo "Mode:         shell-only (no Python 3.9+)"
  echo "Status:       BLOCKED"
  echo "Next action:"
  echo "  - $2"
  exit 2
}

echo "Python 3.9+ not found: shell-only mode (copies AGENTS.md and skills; installs no tools)."

if [ -e "$TARGET/AGENTS.md" ]; then
  if grep -qF -- "$BEGIN_MARK" "$TARGET/AGENTS.md"; then
    note SKIP "AGENTS.md (kit block present)"
  else
    note CONFLICT "AGENTS.md (exists; merging needs Python - add the kit block by hand)"
    CONFLICT=1
  fi
elif [ "$DRY_RUN" -eq 1 ]; then
  note CREATE AGENTS.md
else
  tmp="$TARGET/AGENTS.md.kit-tmp"
  rm -rf "$tmp"
  if ! { { printf '%s\n' "$BEGIN_MARK"; cat "$KIT_ROOT/AGENTS.md"; printf '%s\n' "$END_MARK"; } \
    > "$tmp" && mv "$tmp" "$TARGET/AGENTS.md"; }; then
    rm -f "$tmp"
    fail_blocked "could not write AGENTS.md" "Check that $TARGET is writable, then re-run."
  fi
  note CREATE AGENTS.md
fi

for src in "$KIT_ROOT"/.agents/skills/*/; do
  name="$(basename "$src")"
  dest="$TARGET/.agents/skills/$name"
  if [ -e "$dest" ]; then
    note SKIP ".agents/skills/$name (exists, not checked)"
  elif [ "$DRY_RUN" -eq 1 ]; then
    note CREATE ".agents/skills/$name"
  else
    rm -rf "$dest.kit-tmp"
    if ! { mkdir -p "$TARGET/.agents/skills" && cp -R "${src%/}" "$dest.kit-tmp" \
      && mv "$dest.kit-tmp" "$dest"; }; then
      rm -rf "$dest.kit-tmp"
      fail_blocked "could not copy skill $name" "Check that $TARGET/.agents/skills is writable, then re-run."
    fi
    note CREATE ".agents/skills/$name"
  fi
done

echo "Target:       $TARGET"
echo "Mode:         shell-only (no Python 3.9+)"
echo "Codex load:   UNVERIFIED (open Codex and run /skills)"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN: nothing was written."
  exit 0
fi
if [ "$CONFLICT" -eq 1 ]; then
  echo "Status:       BLOCKED"
  echo "Next action:"
  echo "  - Add the kit block from $KIT_ROOT/AGENTS.md to $TARGET/AGENTS.md by hand, or install Python 3.9+ and re-run."
  exit 2
fi
echo "Status:       PARTIAL"
echo "Next action:"
echo "  - Install Python 3.9+ and re-run to verify files and enable tools/MCP."
echo "  - Open Codex in $TARGET and run /skills to confirm the kit skills load."
exit 1
