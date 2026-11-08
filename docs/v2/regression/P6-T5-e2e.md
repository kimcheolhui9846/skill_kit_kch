# P6-T5 E2E HITL 시나리오

실행 일시: 2026-11-08. 테스트는 `tests/test_p6_e2e.py`, 원본 출력은 `raw/p6t5-*`에 있다.

## 실행 방식

- **픽스처 프로젝트:** 임시 폴더 `e2e 프로젝트`(공백·한글 경로)에 `calc.py`, `tests/test_calc.py`, `pytest.ini`를 둔다.
- **키트 호출:** 매번 새 `python -I run_kit.py …` 프로세스로 실행한다. `bootstrap`이 부르는 방식과 같다.
  - stdin을 닫아 터미널이 없게 했다.
  - HOME, `USERPROFILE`, `CODEX_HOME`, `CLAUDE_CONFIG_DIR`은 임시 폴더를 가리킨다.
  - 호출 사이에 남는 것은 `.kit/` 아래 파일뿐이다. 그래서 "세션 중단 뒤 재시작"은 그냥 다음 프로세스다.
- **JUnit:** 픽스처 프로젝트에서 pytest를 실제로 실행해 만든 `out/junit.xml`을 쓴다.
  - `kit report tests`로 증거 표를 만들고, 그 행을 보고서 4절에 붙인다. 사람이 하는 방식과 같다.
- **구조:** 시나리오는 모듈 픽스처에서 한 번 실행한다. 단계마다 별도 테스트가 결과를 검사한다.

## 단계별 결과

| 단계 | 테스트 | 확인한 것 | 결과 |
|---|---|---|---|
| 1 | `test_step1_requirements_and_dependent_tasks` | REQ-001~003 등록(r1). T-1, T-2(T-2는 T-1에 의존) 모두 TODO. 시작 가능은 T-1뿐 | PASS |
| 2 | `test_step2_submit_needs_the_report_and_the_evidence` | 보고서 없는 submit은 거부(2, "does not exist … kit task report T-1"). 빈 템플릿도 거부(2, REQ-001·REQ-002의 테스트 행 없음). 실제 pytest 실행 → `report tests`가 PASS 2. REQ-003(T-2 몫)은 테스트가 없어 설계대로 PARTIAL(1). 표를 붙인 보고서로 submit은 0 | PASS |
| 3 | `test_step3_dependent_task_waits_for_approval` | T-1 승인 전 T-2 시작은 종료 코드 2, "cannot start T-2: T-1 is SUBMITTED, not APPROVED". 승인 전에는 HANDOFF.md가 없음 | PASS |
| 4 | `test_step4_approval_updates_handoff` | 터미널이 없으면 기본 `human-cli` 승인은 거부(2). `--by agent-recorded --evidence "승인"`으로 승인(0)하면 "Handoff … updated". `.kit/work/HANDOFF.md`에 표시 줄, T-1 제목, 기록 방식, PASS 2, 보고서 9절의 다음 계획, 승인 이력 행이 있음 | PASS |
| 5 | `test_step5_recover_keeps_approved_and_wip_apart` | T-2 시작(0) → `recover save`로 WIP 저장 → 새 프로세스의 `recover`(0). JSON: 승인 목록 `["T-1"]`, 마지막 승인 T-1, 현재 Task T-2 IN_PROGRESS, 테스트 `{"PASS": 2}`. WIP는 따로(task T-2, 메모), 오래됐다는 표시 없음. 텍스트: 메모는 "Temporary (not approved" 아래에만 있음. HANDOFF.md에는 WIP 메모가 없음 | PASS |
| 6 | `test_step6_revised_requirement_names_the_tests_to_review` | `req edit REQ-002 --text …` → r2, "Review: TC-002 … (saw r1)". `req impact REQ-002`: 테스트 TC-002, 검토 대상 TC-002. `req impact REQ-001`: 검토 대상 없음. `trace check`도 TC-002를 지적 | PASS |
| - | `test_scenario_left_home_alone_and_used_no_terminal` | 임시 HOME에 파일 0개. 키트 호출 25번 이상 | PASS |

전체 테스트(Windows, Python 3.12.10): **1435 passed, 2 skipped**(`raw/p6t5-pytest.txt`, `raw/p6t5-junit.xml`). P6-T4 대비 7개 늘었다.

## 변이 점검

키트 코드를 하나씩 고장 내고 `tests/test_p6_e2e.py`만 실행했다. 매번 원래 바이트로 되돌렸다.

| 변이 | 결과 |
|---|---|
| M1 의존 Task의 승인 여부를 보지 않음(`tasks.blockers`) | 잡힘(1단계: 시작 가능 목록에 T-2가 들어감) |
| M2 보고서가 없어도 submit 허용(`tasks.check_report`) | 잡힘(시나리오 픽스처가 실패) |
| M3 승인 뒤 HANDOFF를 갱신하지 않음(`task_cli`) | 잡힘(HANDOFF.md 없음) |
| M4 진행 중 Task를 승인 목록에 섞음(`recover.recover`) | 잡힘(5단계) |
| M5 요구사항을 개정해도 검토 대상 테스트를 찾지 않음(`trace_cli`) | 잡힘(6단계) |
| M6 터미널이 없어도 `human-cli` 승인 허용(`task_cli._confirm`) | 잡힘(4단계) |

## 한계

| 항목 | 상태 | 이유 |
|---|---|---|
| 사람이 터미널에서 Task ID를 다시 입력하는 `human-cli` 승인 | 이 시나리오에서는 NOT RUN | 자동 테스트에는 터미널이 없다. 그래서 에이전트 경로(`agent-recorded`)로 승인했다. `human-cli`의 입력 확인은 `tests/hitl/test_tasks.py`가 in-process로 검사한다 |
| L2 훅 승인(`human-hook`) | 이 시나리오 밖 | `tests/hitl/test_approval_hook.py`가 다룬다 |
| Linux에서 이 파일 실행 | NOT RUN | P6-T4의 WSL 사본은 지웠다. 이 테스트는 표준 라이브러리 하위 프로세스와 pytest만 쓴다 |
