"""MCP smoke test over stdio (initialize -> tools/list) and Codex's own view of the server."""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import tools
from .mcpconfig import select_servers
from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult
from .preflight import EnvReport

PROTOCOL_VERSION = "2025-06-18"
HANDSHAKE_TIMEOUT = 120.0  # first start downloads the package through npx


def find_command(name: str) -> str | None:
    return shutil.which(name)


def _stop(proc: subprocess.Popen) -> None:
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def handshake(command: list[str], timeout: float = HANDSHAKE_TIMEOUT) -> tuple[str, str]:
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return FAIL, f"cannot start server: {exc}"
    lines: queue.Queue = queue.Queue()

    def pump() -> None:
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout

    def send(message: dict) -> None:
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def reply(request_id: int) -> dict:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            line = lines.get(timeout=remaining)
            if line is None:
                raise EOFError
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "hackathon-kit", "version": "1"},
                },
            }
        )
        if "error" in reply(1):
            return FAIL, "initialize was rejected"
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        result = reply(2).get("result")
    except (TimeoutError, queue.Empty):
        return FAIL, f"no response within {timeout:.0f}s"
    except (EOFError, OSError):
        return FAIL, "server exited before answering"
    finally:
        _stop(proc)
    listed = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(listed, list) or not listed:
        return FAIL, "server listed no tools"
    names = ", ".join(str(t.get("name", "?")) for t in listed[:3] if isinstance(t, dict))
    return PASS, f"{len(listed)} tool(s): {names}"


def codex_lists(codex_path: str, target: Path, name: str, runner=None) -> bool | None:
    """True/False when `codex mcp list --json` answered; None when it could not be read."""
    runner = runner or tools.run_command
    code, output = runner([codex_path, "mcp", "list", "--json"], 60.0, target)
    if code != 0 or "[" not in output:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(output[output.index("[") :])
    except ValueError:
        return None
    if not isinstance(data, list):
        return None
    return any(isinstance(e, dict) and e.get("name") == name for e in data)


def _codex_item(name: str, env: EnvReport, target: Path) -> ItemResult:
    label = f"codex-mcp:{name}"
    codex = env.tools.get("codex")
    if codex is None or not codex.ok or not codex.path:
        detail = "codex not found; check /mcp in Codex"
        return ItemResult(label, False, True, False, UNVERIFIED, detail)
    if codex_lists(codex.path, target, name):
        return ItemResult(label, False, True, True, PASS, "listed by `codex mcp list`")
    detail = "not listed by `codex mcp list`; trust this project in Codex, then check /mcp"
    return ItemResult(label, False, True, False, UNVERIFIED, detail)


def check_servers(
    kit_root: Path,
    names: list[str],
    env: EnvReport,
    target: Path,
    offline: bool,
    no_mcp: bool,
    cli_check: bool = True,
) -> list[ItemResult]:
    items = []
    for name, entry in select_servers(kit_root, names):
        label = f"mcp:{name}"
        if no_mcp:
            items.append(ItemResult(label, False, False, False, SKIPPED, "--no-mcp"))
            continue
        if offline:
            detail = "offline: npx would download the package"
            items.append(ItemResult(label, False, False, False, SKIPPED, detail))
            continue
        exe = find_command(entry["command"])
        if exe is None:
            detail = f"{entry['command']} not found; install Node.js or use --no-mcp"
            items.append(ItemResult(label, False, False, False, FAIL, detail))
            continue
        verdict, detail = handshake([exe, *entry["args"]])
        items.append(ItemResult(label, False, True, True, verdict, detail))
        if cli_check:
            items.append(_codex_item(name, env, target))
    return items
