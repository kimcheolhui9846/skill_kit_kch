| REQ | 구현 상태 | 테스트(파일) | 실행 결과 | 비고 |
|---|---|---|---|---|
| REQ-COMPAT-001 | 구현 | `golden/test_golden_legacy.py`, `test_cli.py`, `cli/test_commands.py`, `adapters/test_adapters.py` | PASS (63 passed) | 골든 기준선 24개 |
| REQ-COMPAT-002 | 구현 | `catalog/test_skill_tree.py`, `test_skills.py`, `catalog/test_sources.py` | PASS (79 passed) | v1 스킬은 8개가 아니라 11개(P1에서 확인) |
| REQ-COMPAT-003 | 구현 | `profiles/test_profile_resolver.py`, `test_profiles.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (39 passed) |  |
| REQ-COMPAT-004 | 구현 | `cli/test_install_cleanup.py`, `writers/test_manifest.py`, `cli/test_lifecycle.py`, `cli/test_commands.py` | PASS (20 passed) | v1 위 standard 직접 설치의 정리(후속 3, 2026-11-08). P7-T1에서 찾은 결함 수정 |
| REQ-COMPAT-005 | 구현 | `test_model.py`, `cli/test_commands.py`, `cli/test_entrypoints_v2.py`, `test_entrypoints.py` | PASS (28 passed) |  |
| REQ-COMPAT-006 | 구현 | `test_entrypoints.py`, `cli/test_entrypoints_v2.py` | PASS (20 passed) |  |
| REQ-COMPAT-007 | 구현 | `test_stdlib_only.py`, `test_p6_platform.py` | PASS (73 passed) | TC-SEC-01 AST 검사(후속 2). 3.9 실제 실행은 P6-T4(Linux 3.9.25) |
| REQ-ARCH-001 | 구현 | `catalog/test_skill_tree.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (4 passed) |  |
| REQ-ARCH-002 | 구현 | `catalog/test_mcp_catalog.py`, `catalog/test_plugin_install.py`, `catalog/test_skill_tree.py` | PASS (3 passed) |  |
| REQ-ARCH-003 | 구현 | `adapters/test_adapters.py`, `cli/test_commands.py` | PASS (2 passed) |  |
| REQ-ARCH-004 | 구현 | `adapters/test_adapters.py`, `profiles/test_profile_resolver.py` | PASS (2 passed) |  |
| REQ-AGENT-001 | 구현 | `cli/test_commands.py` | PASS (4 passed) |  |
| REQ-AGENT-002 | 구현 | `adapters/test_claude_adapter.py`, `cli/test_commands.py` | PASS (2 passed) | 위치 근거: 02_COMPATIBILITY_MATRIX.md |
| REQ-AGENT-003 | 구현 | `test_p6_matrix.py`, `adapters/test_claude_adapter.py`, `cli/test_commands.py`, `cli/test_lifecycle.py` | PASS (4 passed) |  |
| REQ-AGENT-004 | 구현 | `test_p6_agent_load_check.py` | PASS (4 passed) | 문서: 02_COMPATIBILITY_MATRIX.md(행마다 출처·확인 수준). 매트릭스 자체를 검사하는 테스트는 없음 |
| REQ-AGENT-005 | 구현 | `adapters/test_claude_adapter.py`, `test_p6_agent_load_check.py` | PASS (5 passed) | 실제 로드는 AGENT_LOAD_CHECK.md(검토자, NOT RUN) |
| REQ-INST-001 | 구현 | `cli/test_commands.py` | PASS (3 passed) |  |
| REQ-INST-002 | 구현 | `cli/test_commands.py`, `cli/test_network.py` | PASS (6 passed) |  |
| REQ-INST-003 | 구현 | `cli/test_commands.py`, `test_verify.py` | PASS (10 passed) |  |
| REQ-INST-004 | 구현 | `cli/test_commands.py` | PASS (2 passed) |  |
| REQ-INST-005 | 구현 | `cli/test_lifecycle.py` | PASS (4 passed) |  |
| REQ-INST-006 | 구현 | `cli/test_lifecycle.py` | PASS (6 passed) |  |
| REQ-INST-007 | 구현 | `cli/test_commands.py`, `cli/test_network.py`, `test_p6_matrix.py` | PASS (4 passed) |  |
| REQ-INST-008 | 구현 | `cli/test_lifecycle.py`, `cli/test_commands.py` | PASS (6 passed) |  |
| REQ-INST-009 | 구현 | `cli/test_commands.py`, `test_report.py`, `cli/test_network.py` | PASS (14 passed) |  |
| REQ-INST-010 | 구현 | `test_p6_matrix.py`, `test_p6_platform.py` | PASS (11 passed) | Linux는 P6-T4(WSL2). PowerShell 7·실제 Linux 기기는 NOT RUN |
| REQ-SAFE-001 | 구현 | `test_p6_matrix.py`, `adapters/test_claude_adapter.py`, `writers/test_json_keys.py`, `test_agentsmd.py` | PASS (24 passed) |  |
| REQ-SAFE-002 | 구현 | `test_register.py`, `cli/test_lifecycle.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-SAFE-003 | 구현 | `writers/test_json_keys.py`, `cli/test_lifecycle.py` | PASS (18 passed) |  |
| REQ-SAFE-004 | 구현 | `test_p6_matrix.py`, `test_idempotency.py`, `cli/test_commands.py`, `adapters/test_claude_adapter.py` | PASS (8 passed) |  |
| REQ-SAFE-005 | 구현 | `cli/test_commands.py`, `cli/test_lifecycle.py`, `test_failure_recovery.py`, `test_blocked_on_error.py` | PASS (18 passed) |  |
| REQ-SAFE-006 | 구현 | `cli/test_network.py`, `test_p6_matrix.py` | PASS (13 passed) |  |
| REQ-SAFE-007 | 구현 | `test_p6_matrix.py`, `test_security.py`, `cli/test_network.py` | PASS (19 passed) |  |
| REQ-SAFE-008 | 구현 | `test_p6_matrix.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-SAFE-009 | 구현 | `catalog/test_mcp_catalog.py`, `adapters/test_claude_adapter.py`, `cli/test_commands.py`, `test_audit.py` | PASS (30 passed) |  |
| REQ-SAFE-010 | 구현 | `test_p6_matrix.py`, `cli/test_commands.py`, `cli/test_lifecycle.py`, `userscope/test_user_install.py` | PASS (6 passed) |  |
| REQ-SAFE-011 | 구현 | `catalog/test_p4t9_credentials.py` | PASS (36 passed) | P4-T9 결정 |
| REQ-SAFE-012 | 구현 | `cli/test_p4t9_followups.py` | PASS (17 passed) | 2026-11-06 결정 |
| REQ-PROF-001 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (14 passed) |  |
| REQ-PROF-002 | 구현 | `profiles/test_profile_resolver.py` | PASS (19 passed) |  |
| REQ-PROF-003 | 구현 | `profiles/test_profile_resolver.py` | PASS (2 passed) |  |
| REQ-PROF-004 | 구현 | `profiles/test_profile_resolver.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (17 passed) |  |
| REQ-PROF-005 | 구현 | `profiles/test_profile_resolver.py`, `cli/test_commands.py` | PASS (2 passed) | 보여 주는 목록은 정책 적용 전(11개). standard 실제 설치는 17개(검토자 결정 대기) |
| REQ-SRC-001 | 구현 | - | 문서 | 문서: 07_SOURCES_EVALUATION.md |
| REQ-SRC-002 | 구현 | `catalog/test_sources.py`, `test_p6_security.py` | PASS (19 passed) |  |
| REQ-SRC-003 | 구현 | `catalog/test_sources.py`, `test_skills.py` | PASS (4 passed) |  |
| REQ-SRC-004 | 구현 | `sources/test_source_add.py` | PASS (2 passed) | P4-T3 중간 승인 기록 |
| REQ-SRC-005 | 구현 | `catalog/test_sources.py`, `sources/test_source_add.py` | PASS (6 passed) | 비교표: 07_SOURCES_EVALUATION.md |
| REQ-SRC-006 | 구현 | - | 문서 | 문서: 08_USER_SOURCES.md |
| REQ-SRC-007 | 구현 | `catalog/test_sources.py`, `catalog/test_skill_tree.py` | PASS (3 passed) |  |
| REQ-SRC-008 | 구현 | - | 문서 | 문서: 07_SOURCES_EVALUATION.md |
| REQ-SRC-009 | 구현 | `sources/test_source_add.py` | PASS (81 passed) |  |
| REQ-POL-001 | 구현 | `profiles/test_p4t6_profiles_policy.py`, `profiles/test_p5t1_skill_guide.py` | PASS (23 passed) |  |
| REQ-POL-002 | 구현 | `profiles/test_p4t6_profiles_policy.py`, `cli/test_commands.py` | PASS (3 passed) |  |
| REQ-POL-003 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (1 passed) |  |
| REQ-POL-004 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (1 passed) |  |
| REQ-HITL-001 | 구현 | `hitl/test_tasks.py` | PASS (9 passed) |  |
| REQ-HITL-002 | 구현 | `hitl/test_tasks.py` | PASS (2 passed) |  |
| REQ-HITL-003 | 구현 | `hitl/test_tasks.py`, `test_p6_e2e.py` | PASS (10 passed) |  |
| REQ-HITL-004 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (3 passed) | §5.3 조건 9개를 standard 정책 Approval 절에 둠(후속 1, 2026-11-08) |
| REQ-HITL-005 | 구현 | `hitl/test_tasks.py` | PASS (10 passed) |  |
| REQ-HITL-006 | 구현 | `hitl/test_tasks.py`, `hitl/test_approval_hook.py` | PASS (83 passed) | L2 훅 실제 동작은 M-05 VERIFIED-RUN(2026-11-07) |
| REQ-TEST-001 | 구현 | `hitl/test_report_tests.py` | PASS (4 passed) |  |
| REQ-TEST-002 | 구현 | `hitl/test_report_tests.py`, `test_p6_e2e.py` | PASS (30 passed) |  |
| REQ-TRACE-001 | 구현 | `hitl/test_trace.py` | PASS (14 passed) |  |
| REQ-TRACE-002 | 구현 | `hitl/test_trace.py` | PASS (1 passed) |  |
| REQ-TRACE-003 | 구현 | `hitl/test_trace.py` | PASS (14 passed) |  |
| REQ-TRACE-004 | 구현 | `hitl/test_trace.py`, `test_p6_e2e.py` | PASS (17 passed) |  |
| REQ-TRACE-005 | 구현 | `hitl/test_report_tests.py` | PASS (7 passed) |  |
| REQ-CE-001 | 구현 | `hitl/test_counterexamples.py` | PASS (27 passed) |  |
| REQ-CE-002 | 구현 | `hitl/test_counterexamples.py` | PASS (4 passed) |  |
| REQ-ALGO-001 | 구현 | `catalog/test_p5t6_skills.py` | PASS (1 passed) |  |
| REQ-DATA-001 | 구현 | `catalog/test_p5t6_skills.py` | PASS (14 passed) |  |
| REQ-SESS-001 | 구현 | `hitl/test_recover.py`, `test_p6_e2e.py` | PASS (23 passed) |  |
| REQ-SESS-002 | 구현 | `hitl/test_recover.py` | PASS (11 passed) |  |
| REQ-SESS-003 | 구현 | `hitl/test_recover.py` | PASS (4 passed) |  |
| REQ-SKILL-001 | 구현 | `catalog/test_launch_compliance.py` | PASS (34 passed) | TC-SKL-05(후속 4). 한국 법령 인용은 원문 미확인이라 UNVERIFIED |
| REQ-USER-001 | 구현 | `userscope/test_capture.py` | PASS (10 passed) |  |
| REQ-USER-002 | 구현 | `userscope/test_user_install.py` | PASS (10 passed) | 실제 홈 적용(M-06)은 NOT RUN |
| REQ-USER-003 | 구현 | `userscope/test_capture.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-USER-004 | 구현 | `userscope/test_capture.py` | PASS (10 passed) |  |
| REQ-USER-005 | 구현 | `userscope/test_user_install.py`, `catalog/test_sources.py` | PASS (4 passed) | 실제 Codex 로드는 AGENT_LOAD_CHECK.md |
| REQ-USER-008 | 구현 | `userscope/test_own_files.py` | PASS (10 passed, 1 skipped) | Q4 결정(2026-11-06) |
| REQ-DOC-001 | 구현 | `test_doc_commands.py`, `test_catalog_doc.py` | PASS (76 passed) | §12 문서 13종. 문서 명령 95개 실행 기록: P7-T1-doc-commands.md |

PASS 81, 문서 3
