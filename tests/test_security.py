import re

from kit.logs import mask

FORBIDDEN = [
    re.compile(r"git\s+push"),
    re.compile(r"curl[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"\|\s*iex\b", re.IGNORECASE),
    re.compile(r"Invoke-Expression", re.IGNORECASE),
    re.compile(r"https?://[^\s\"']*(telemetry|analytics|sentry|segment)", re.IGNORECASE),
]
NETWORK_IMPORT = re.compile(r"^\s*(import|from)\s+(socket|urllib|http)\b", re.MULTILINE)
CODE_GLOBS = [
    "kit/*.py",
    "run_kit.py",
    "bootstrap.sh",
    "bootstrap.ps1",
    "mcp/*.json",
    "profiles/*.json",
]


def test_mask_hides_tokens():
    text = (
        "sk-abcdefghijklmnopqrstuv ghp_ABCDEFGHIJKLMNOPQRSTUVWX12 "
        "API_KEY=hunter2 password: opensesame"
    )
    masked = mask(text)
    for secret in (
        "sk-abcdefghijklmnopqrstuv",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWX12",
        "hunter2",
        "opensesame",
    ):
        assert secret not in masked
    assert "API_KEY=***" in masked


def test_log_never_contains_environment_values(run_kit, workspace, monkeypatch):
    monkeypatch.setenv("KIT_TEST_SECRET", "ghp_" + "Z" * 30)
    run_kit()
    logs = list((workspace / ".kit" / "logs").glob("*.log"))
    assert logs
    for log in logs:
        assert "ZZZZZZZZZZ" not in log.read_text(encoding="utf-8")


# P4-T8 (ADR-021): `kit source` scans downloads for remote-script one-liners, so the detector
# names them; it may not run anything. The GitHub client is the kit's only network code.
DETECTOR = "kit/source_scan.py"
NETWORK_MODULE = "kit/github_fetch.py"
RUNS_THINGS = re.compile(r"\b(subprocess|os\.system|os\.popen|exec\(|eval\(|__import__)")


def test_kit_code_has_no_push_or_pipe_to_shell(kit_root):
    files = [p for pattern in CODE_GLOBS for p in kit_root.glob(pattern)]
    assert files
    for path in files:
        if path.relative_to(kit_root).as_posix() == DETECTOR:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            assert not pattern.search(text), f"{path.name}: {pattern.pattern}"


def test_the_detector_runs_nothing_and_has_no_network(kit_root):
    text = (kit_root / DETECTOR).read_text(encoding="utf-8")
    assert not RUNS_THINGS.search(text)
    assert not NETWORK_IMPORT.search(text)
    assert "git push" not in text


def test_kit_core_imports_no_network_modules(kit_root):
    for path in kit_root.glob("kit/*.py"):
        if path.relative_to(kit_root).as_posix() == NETWORK_MODULE:
            continue
        assert not NETWORK_IMPORT.search(path.read_text(encoding="utf-8")), path.name


def test_the_network_module_reads_github_only(kit_root):
    text = (kit_root / NETWORK_MODULE).read_text(encoding="utf-8")
    hosts = set(re.findall(r"https?://([^/\"'\s]+)", text))
    assert hosts == {"api.github.com", "codeload.github.com"}
    assert not RUNS_THINGS.search(text)
    assert not re.search(r"\.(post|put|delete|patch)\(|method=", text, re.IGNORECASE)


def test_kit_mcp_data_contains_no_remote_endpoints(kit_root):
    for path in kit_root.glob("mcp/*.json"):
        assert not re.search(r"https?://", path.read_text(encoding="utf-8")), path.name


def test_no_writes_outside_target(run_kit, workspace, tmp_path):
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    run_kit()
    assert list(sibling.iterdir()) == []


def test_mask_hides_prefixed_names_and_bearer_values():
    text = (
        "GITHUB_TOKEN=abc123 OPENAI_API_KEY=xyz MY_SECRET=s3 "
        "token: Bearer qq Authorization: Bearer zz"
    )
    masked = mask(text)
    for secret in ("abc123", "xyz", "s3", "qq", "zz"):
        assert secret not in masked
    assert "GITHUB_TOKEN=***" in masked and "OPENAI_API_KEY=***" in masked
