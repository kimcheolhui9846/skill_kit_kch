"""Requirement coverage from a JUnit file (P7-T2, 00_PROMPT 16 section 4).

    uv run --offline pytest -q -p no:cacheprovider --junitxml=<file>
    uv run python devtools/req_coverage.py <file> [--out <markdown>]

Every requirement of 00_PROMPT 4 and 00_ADDENDUM (and the three later decisions SAFE-011,
SAFE-012, USER-008) is mapped below to the tests that check it, as `file` or `file::name`
patterns (a name pattern is a regular expression matched at the start of the test name, after
`test_`). The result columns come only from the JUnit file: a requirement whose patterns match
no test case there is NOT RUN. Documents and manual checks are named in the note column; they
are not counted as test results.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple

ROOT = Path(__file__).resolve().parent.parent


class Req(NamedTuple):
    impl: str  # 구현 / 부분 / 미구현
    tests: Tuple[str, ...]
    note: str = ""


MAP: Dict[str, Req] = {
    # COMPAT
    "COMPAT-001": Req(
        "구현",
        (
            "tests/golden/test_golden_legacy.py",
            "tests/test_cli.py",
            "tests/cli/test_commands.py::unknown_first_word_stays_on_legacy_path",
            "tests/adapters/test_adapters.py::codex_plan_equals_legacy_plan",
        ),
        "골든 기준선 24개",
    ),
    "COMPAT-002": Req(
        "구현",
        (
            "tests/catalog/test_skill_tree.py::(restricted_catalog|layered_files_equal|agents_skills)",
            "tests/test_skills.py",
            "tests/catalog/test_sources.py::restricted_new_path",
        ),
        "v1 스킬은 8개가 아니라 11개(P1에서 확인)",
    ),
    "COMPAT-003": Req(
        "구현",
        (
            "tests/profiles/test_profile_resolver.py::(v1_|full_keeps)",
            "tests/test_profiles.py",
            "tests/profiles/test_p4t6_profiles_policy.py::(legacy_path_sees|v1_profile_files)",
        ),
    ),
    "COMPAT-004": Req(
        "구현",
        (
            "tests/cli/test_install_cleanup.py",
            "tests/writers/test_manifest.py::adopt_",
            "tests/cli/test_lifecycle.py::uninstall_legacy_install",
            "tests/cli/test_commands.py::verify_accepts_a_legacy_install",
        ),
        "v1 위 standard 직접 설치의 정리(후속 3, 2026-11-08). P7-T1에서 찾은 결함 수정",
    ),
    "COMPAT-005": Req(
        "구현",
        (
            "tests/test_model.py",
            "tests/cli/test_commands.py::(usage_errors_exit_64|target_errors_exit_65)",
            "tests/cli/test_entrypoints_v2.py::usage_error_code_passes_through",
            "tests/test_entrypoints.py::(bad_argument|missing_target)",
        ),
    ),
    "COMPAT-006": Req(
        "구현",
        (
            "tests/test_entrypoints.py::fallback_",
            "tests/cli/test_entrypoints_v2.py::shell_only_mode_rejects_subcommands",
        ),
    ),
    "COMPAT-007": Req(
        "구현",
        ("tests/test_stdlib_only.py", "tests/test_p6_platform.py::without_tomllib"),
        "TC-SEC-01 AST 검사(후속 2). 3.9 실제 실행은 P6-T4(Linux 3.9.25)",
    ),
    # ARCH
    "ARCH-001": Req(
        "구현",
        (
            "tests/catalog/test_skill_tree.py::(shared_and_agent_layers|install_puts_each_layer)",
            "tests/profiles/test_p4t6_profiles_policy.py::(each_rule_has_one_source|editing_one)",
        ),
    ),
    "ARCH-002": Req(
        "구현",
        (
            "tests/catalog/test_mcp_catalog.py::plugin_is_declared_for_claude_only",
            "tests/catalog/test_plugin_install.py::each_agent_gets_only_its_own_plugins",
            "tests/catalog/test_skill_tree.py::editing_an_agent_layer",
        ),
    ),
    "ARCH-003": Req(
        "구현",
        (
            "tests/adapters/test_adapters.py::new_agent_needs_only_adapter_and_registry",
            "tests/cli/test_commands.py::every_registered_agent_has_a_cli_name",
        ),
    ),
    "ARCH-004": Req(
        "구현",
        (
            "tests/adapters/test_adapters.py::plan_is_pure",
            "tests/profiles/test_profile_resolver.py::resolver_is_read_only",
        ),
    ),
    # AGENT
    "AGENT-001": Req(
        "구현",
        (
            "tests/cli/test_commands.py::(codex_install|claude_install|both_installs"
            "|plan_output_lists_each_agent)",
        ),
    ),
    "AGENT-002": Req(
        "구현",
        (
            "tests/adapters/test_claude_adapter.py::files_land_in_documented_places",
            "tests/cli/test_commands.py::claude_install_writes_only_claude_files",
        ),
        "위치 근거: 02_COMPATIBILITY_MATRIX.md",
    ),
    "AGENT-003": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v07",
            "tests/adapters/test_claude_adapter.py::codex_files_untouched",
            "tests/cli/test_commands.py::claude_after_codex",
            "tests/cli/test_lifecycle.py::codex_untouched",
        ),
    ),
    "AGENT-004": Req(
        "구현",
        ("tests/test_p6_agent_load_check.py",),
        "문서: 02_COMPATIBILITY_MATRIX.md(행마다 출처·확인 수준). "
        "매트릭스 자체를 검사하는 테스트는 없음",
    ),
    "AGENT-005": Req(
        "구현",
        (
            "tests/adapters/test_claude_adapter.py::manual_checks_mention",
            "tests/test_p6_agent_load_check.py",
        ),
        "실제 로드는 AGENT_LOAD_CHECK.md(검토자, NOT RUN)",
    ),
    # INST
    "INST-001": Req(
        "구현",
        ("tests/cli/test_commands.py::(codex_install|claude_install|both_installs)",),
    ),
    "INST-002": Req(
        "구현",
        (
            "tests/cli/test_commands.py::(plan_and_dry_run|plan_output|plan_json)",
            "tests/cli/test_network.py::plan_lists_network",
        ),
    ),
    "INST-003": Req("구현", ("tests/cli/test_commands.py::verify_", "tests/test_verify.py")),
    "INST-004": Req("구현", ("tests/cli/test_commands.py::doctor_",)),
    "INST-005": Req("구현", ("tests/cli/test_lifecycle.py::update_",)),
    "INST-006": Req("구현", ("tests/cli/test_lifecycle.py::uninstall_",)),
    "INST-007": Req(
        "구현",
        (
            "tests/cli/test_commands.py::offline_",
            "tests/cli/test_network.py::offline_",
            "tests/test_p6_matrix.py::v09",
        ),
    ),
    "INST-008": Req(
        "구현",
        (
            "tests/cli/test_lifecycle.py::restore_",
            "tests/cli/test_commands.py::conflict_in_one_agent",
        ),
    ),
    "INST-009": Req(
        "구현",
        (
            "tests/cli/test_commands.py::(report_json_file|plan_json_is_one)",
            "tests/test_report.py",
            "tests/cli/test_network.py::new_path_masks_stdout_log_and_json",
        ),
    ),
    "INST-010": Req(
        "구현",
        ("tests/test_p6_matrix.py::v16", "tests/test_p6_platform.py"),
        "Linux는 P6-T4(WSL2). PowerShell 7·실제 Linux 기기는 NOT RUN",
    ),
    # SAFE
    "SAFE-001": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v05",
            "tests/adapters/test_claude_adapter.py::existing_claude_md",
            "tests/writers/test_json_keys.py::user_keys_order",
            "tests/test_agentsmd.py",
        ),
    ),
    "SAFE-002": Req(
        "구현",
        (
            "tests/test_register.py::apply_backs_up",
            "tests/cli/test_lifecycle.py::(uninstall_keeps_backups|restore_puts_back)",
            "tests/userscope/test_user_install.py::backups_restore",
        ),
    ),
    "SAFE-003": Req(
        "구현",
        (
            "tests/writers/test_json_keys.py",
            "tests/cli/test_lifecycle.py::(user_modified_items|edited_kit_block)",
        ),
    ),
    "SAFE-004": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v04",
            "tests/test_idempotency.py",
            "tests/cli/test_commands.py::rerun_is_idempotent",
            "tests/adapters/test_claude_adapter.py::rerun_is_idempotent",
        ),
    ),
    "SAFE-005": Req(
        "구현",
        (
            "tests/cli/test_commands.py::both_rolls_back",
            "tests/cli/test_lifecycle.py::exception_mid_",
            "tests/test_failure_recovery.py",
            "tests/test_blocked_on_error.py",
        ),
    ),
    "SAFE-006": Req(
        "구현",
        (
            "tests/cli/test_network.py::(non_interactive|yes_allows|terminal_prompt"
            "|no_prompt|offline_never|plan_lists|no_mcp|offline_makes)",
            "tests/test_p6_matrix.py::v09",
        ),
    ),
    "SAFE-007": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v17",
            "tests/test_security.py::(mask|log_never)",
            "tests/cli/test_network.py::(mask_covers|find_reports|new_path_masks)",
        ),
    ),
    "SAFE-008": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v18",
            "tests/userscope/test_user_install.py::project_scope_never_touches_home",
        ),
    ),
    "SAFE-009": Req(
        "구현",
        (
            "tests/catalog/test_mcp_catalog.py::(every_high_risk|no_plugin_without|listed_only"
            "|off_by_default|audit_still)",
            "tests/adapters/test_claude_adapter.py::mcp_outside_allowlist",
            "tests/cli/test_commands.py::mcp_outside_the_catalog_is_64",
            "tests/test_audit.py",
        ),
    ),
    "SAFE-010": Req(
        "구현",
        (
            "tests/test_p6_matrix.py::v08",
            "tests/cli/test_commands.py::plan_and_dry_run",
            "tests/cli/test_lifecycle.py::uninstall_dry_run",
            "tests/userscope/test_user_install.py::dry_run_leaves_home",
        ),
    ),
    "SAFE-011": Req("구현", ("tests/catalog/test_p4t9_credentials.py",), "P4-T9 결정"),
    "SAFE-012": Req("구현", ("tests/cli/test_p4t9_followups.py",), "2026-11-06 결정"),
    # PROF
    "PROF-001": Req(
        "구현", ("tests/profiles/test_p4t6_profiles_policy.py::(new_profile|hackathon_)",)
    ),
    "PROF-002": Req(
        "구현",
        (
            "tests/profiles/test_profile_resolver.py::(hitl_pack|multi_extends|combination"
            "|packs_field|reference_errors|diamond|scalar|child_policy)",
        ),
    ),
    "PROF-003": Req(
        "구현",
        ("tests/profiles/test_profile_resolver.py::(shared_codex_claude|profile_not_for_agent)",),
    ),
    "PROF-004": Req(
        "구현",
        (
            "tests/profiles/test_profile_resolver.py::v1_",
            "tests/profiles/test_p4t6_profiles_policy.py::v1_profile_files",
        ),
    ),
    "PROF-005": Req(
        "구현",
        (
            "tests/profiles/test_profile_resolver.py::show_matches",
            "tests/cli/test_commands.py::profiles_show_matches_resolver",
        ),
        "보여 주는 목록은 정책 적용 전(11개). standard 실제 설치는 17개(검토자 결정 대기)",
    ),
    # SRC
    "SRC-001": Req("구현", (), "문서: 07_SOURCES_EVALUATION.md"),
    "SRC-002": Req(
        "구현",
        (
            "tests/catalog/test_sources.py::(real_lock|lock_schema|bad_file_path|check_reports"
            "|tampered)",
            "tests/test_p6_security.py::(every_external_file|a_changed_byte)",
        ),
    ),
    "SRC-003": Req(
        "구현",
        (
            "tests/catalog/test_sources.py::(every_vendored|check_requires_notices"
            "|installed_vendored)",
            "tests/test_skills.py::third_party_notices",
        ),
    ),
    "SRC-004": Req(
        "구현",
        ("tests/sources/test_source_add.py::(no_terminal_and_no_yes|check_online_needs)",),
        "P4-T3 중간 승인 기록",
    ),
    "SRC-005": Req(
        "구현",
        (
            "tests/catalog/test_sources.py::(standard_replaces|same_name_resolves)",
            "tests/sources/test_source_add.py::(name_clash|similar_skill|keep_both|unrelated)",
        ),
        "비교표: 07_SOURCES_EVALUATION.md",
    ),
    "SRC-006": Req("구현", (), "문서: 08_USER_SOURCES.md"),
    "SRC-007": Req(
        "구현",
        (
            "tests/catalog/test_sources.py::(restricted_new_path|standard_replaces)",
            "tests/catalog/test_skill_tree.py::agents_skills_unchanged",
        ),
    ),
    "SRC-008": Req("구현", (), "문서: 07_SOURCES_EVALUATION.md"),
    "SRC-009": Req("구현", ("tests/sources/test_source_add.py",)),
    # POL
    "POL-001": Req(
        "구현",
        (
            "tests/profiles/test_p4t6_profiles_policy.py::(ten_principles|claude_alone"
            "|each_rule|editing_one)",
            "tests/profiles/test_p5t1_skill_guide.py",
        ),
    ),
    "POL-002": Req(
        "구현",
        (
            "tests/profiles/test_p4t6_profiles_policy.py::(restricted_render|hackathon_restricted)",
            "tests/cli/test_commands.py::restricted_policy_is_the_legacy_text",
        ),
    ),
    "POL-003": Req("구현", ("tests/profiles/test_p4t6_profiles_policy.py::standard_names",)),
    "POL-004": Req("구현", ("tests/profiles/test_p4t6_profiles_policy.py::light_path",)),
    # HITL
    "HITL-001": Req("구현", ("tests/hitl/test_tasks.py::(add_records|bad_add|find_cycle)",)),
    "HITL-002": Req("구현", ("tests/hitl/test_tasks.py::subtasks_",)),
    "HITL-003": Req(
        "구현",
        (
            "tests/hitl/test_tasks.py::(start_waits|only_one|submitted_or_approved)",
            "tests/test_p6_e2e.py",
        ),
    ),
    "HITL-004": Req(
        "구현",
        (
            "tests/profiles/test_p4t6_profiles_policy.py::(mid_task_approval|ten_principles|light_path)",
        ),
        "§5.3 조건 9개를 standard 정책 Approval 절에 둠(후속 1, 2026-11-08)",
    ),
    "HITL-005": Req(
        "구현",
        ("tests/hitl/test_tasks.py::(report_template|submit_needs|submit_checks|not_run_with)",),
    ),
    "HITL-006": Req(
        "구현",
        (
            "tests/hitl/test_tasks.py::(agent_recorded|human_cli|cli_cannot|quote_is"
            "|a_report_changed|a_hand_edited|status_shows)",
            "tests/hitl/test_approval_hook.py",
        ),
        "L2 훅 실제 동작은 M-05 VERIFIED-RUN(2026-11-07)",
    ),
    # TEST
    "TEST-001": Req(
        "구현",
        (
            "tests/hitl/test_report_tests.py::(report_sections|the_table_can|input_and_expected"
            "|unknown_and_unlinked)",
        ),
    ),
    "TEST-002": Req(
        "구현",
        (
            "tests/hitl/test_report_tests.py::(pytest_outcomes|vitest|go_subtests|several_junit"
            "|locator_matching|parametrised|all_skipped|unusable_junit)",
            "tests/test_p6_e2e.py",
        ),
    ),
    # TRACE
    "TRACE-001": Req(
        "구현", ("tests/hitl/test_trace.py::(add_and_list|a_duplicate_id|bad_arguments)",)
    ),
    "TRACE-002": Req("구현", ("tests/hitl/test_trace.py::tests_pointing_nowhere",)),
    "TRACE-003": Req(
        "구현",
        (
            "tests/hitl/test_trace.py::(untested_requirements|a_must_requirement|any_non_normal"
            "|missing_or_empty|a_broken_file)",
        ),
    ),
    "TRACE-004": Req(
        "구현",
        (
            "tests/hitl/test_trace.py::(edit_raises|sync_|impact_after|relinking)",
            "tests/test_p6_e2e.py",
        ),
    ),
    "TRACE-005": Req(
        "구현",
        (
            "tests/hitl/test_report_tests.py::(report_sections|design_section|everything_passing"
            "|anything_short)",
        ),
    ),
    # CE / ALGO / DATA
    "CE-001": Req(
        "구현",
        (
            "tests/hitl/test_counterexamples.py::(add_records|bad_records|duplicates|accept_convert"
            "|needs_spec|rejecting|wrong_transitions|convert_needs|list_shows|report_shows"
            "|standard_claude_install|no_subagent|a_users_own)",
        ),
    ),
    "CE-002": Req(
        "구현",
        ("tests/hitl/test_counterexamples.py::(a_c_grade|other_grades|a_broken_record_file)",),
    ),
    "ALGO-001": Req("구현", ("tests/catalog/test_p5t6_skills.py::standard_algorithm_options",)),
    "DATA-001": Req(
        "구현",
        (
            "tests/catalog/test_p5t6_skills.py::(data_quality|the_policy_says|profile_finds"
            "|markdown_report|cp949|empty_file|errors|mixed_numbers)",
        ),
    ),
    # SESS
    "SESS-001": Req(
        "구현",
        (
            "tests/hitl/test_recover.py::(recover_|an_empty_workspace|submitted_task|a_broken_wip"
            "|snapshot_|no_snapshot|with_git|without_git|decisions_)",
            "tests/test_p6_e2e.py",
        ),
    ),
    "SESS-002": Req(
        "구현",
        (
            "tests/hitl/test_recover.py::(handoff_|approve_writes|a_hook_approval"
            "|a_report_changed_after_approval|wip_of_a_task|save_)",
        ),
    ),
    "SESS-003": Req(
        "구현",
        (
            "tests/hitl/test_recover.py::(a_root_handoff|a_kit_work_handoff|state_files"
            "|a_handoff_path)",
        ),
    ),
    # Addendum
    "SKILL-001": Req(
        "구현",
        ("tests/catalog/test_launch_compliance.py",),
        "TC-SKL-05(후속 4). 한국 법령 인용은 원문 미확인이라 UNVERIFIED",
    ),
    "USER-001": Req(
        "구현",
        ("tests/userscope/test_capture.py::(write_creates|env_and_header|toml_headers|multiline)",),
    ),
    "USER-002": Req(
        "구현",
        (
            "tests/userscope/test_user_install.py::(dry_run|non_interactive|terminal_answer"
            "|scope_user|install_writes|backups|user_edits|large_agents_md)",
        ),
        "실제 홈 적용(M-06)은 NOT RUN",
    ),
    "USER-003": Req(
        "구현",
        (
            "tests/userscope/test_capture.py::(dry_run|write_creates|agent_option)",
            "tests/userscope/test_user_install.py::capture_on_one_pc",
        ),
    ),
    "USER-004": Req(
        "구현",
        (
            "tests/userscope/test_capture.py::(capture_never|names_only|a_secret_in|repo_user"
            "|extra_patterns)",
        ),
    ),
    "USER-005": Req(
        "구현",
        (
            "tests/userscope/test_user_install.py::(omx_|identical_files|capture_on_one_pc)",
            "tests/catalog/test_sources.py::oh_my_codex",
        ),
        "실제 Codex 로드는 AGENT_LOAD_CHECK.md",
    ),
    "USER-008": Req("구현", ("tests/userscope/test_own_files.py",), "Q4 결정(2026-11-06)"),
    # DOC
    "DOC-001": Req(
        "구현",
        ("tests/test_doc_commands.py", "tests/test_catalog_doc.py"),
        "§12 문서 13종. 문서 명령 95개 실행 기록: P7-T1-doc-commands.md",
    ),
}


class Case(NamedTuple):
    path: str
    name: str
    outcome: str  # passed / failed / skipped


def parse_junit(path: Path) -> List[Case]:
    cases = []
    for tc in ET.parse(path).iter("testcase"):
        classname = tc.get("classname") or ""
        rel = classname.replace(".", "/") + ".py"
        outcome = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                outcome = "failed"
            elif child.tag == "skipped":
                outcome = "skipped"
        cases.append(Case(rel, tc.get("name") or "", outcome))
    return cases


def split(pattern: str) -> Tuple[str, str]:
    path, _, name = pattern.partition("::")
    return path, name


def matches(pattern: str, case: Case) -> bool:
    path, name = split(pattern)
    if case.path != path:
        return False
    return not name or re.match(rf"test_(?:{name})", case.name) is not None


def tally(req: Req, cases: List[Case]) -> Counter:
    hit = [c for c in cases if any(matches(p, c) for p in req.tests)]
    return Counter(c.outcome for c in hit)


def status(req: Req, counts: Counter) -> str:
    if not req.tests:
        return "문서" if req.impl != "미구현" else "NOT RUN"
    total = sum(counts.values())
    if total == 0:
        return "NOT RUN"
    if counts["failed"]:
        return "FAIL"
    return "PASS" if counts["passed"] else "SKIPPED"


def files(req: Req) -> str:
    seen: List[str] = []
    for pattern in req.tests:
        path = split(pattern)[0].replace("tests/", "", 1)
        if path not in seen:
            seen.append(path)
    return ", ".join(f"`{p}`" for p in seen) if seen else "-"


def render(cases: List[Case]) -> Tuple[str, Counter]:
    lines = [
        "| REQ | 구현 상태 | 테스트(파일) | 실행 결과 | 비고 |",
        "|---|---|---|---|---|",
    ]
    summary: Counter = Counter()
    for key, req in MAP.items():
        counts = tally(req, cases)
        result = status(req, counts)
        summary[result] += 1
        shown = result
        if sum(counts.values()):
            parts = [f"{counts[k]} {k}" for k in ("passed", "failed", "skipped") if counts[k]]
            shown += f" ({', '.join(parts)})"
        lines.append(f"| REQ-{key} | {req.impl} | {files(req)} | {shown} | {req.note} |")
    return "\n".join(lines) + "\n", summary


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("junit", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    cases = parse_junit(args.junit)
    table, summary = render(cases)
    text = table + "\n" + ", ".join(f"{k} {v}" for k, v in sorted(summary.items())) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
