# 사람이 승인하는 작업 흐름 (HITL)

에이전트가 일을 Task 단위로 나누고, 사람이 보고서를 보고 승인해야 다음 Task로 넘어가게 하는 흐름이다. 상태는 모두 작업 공간의 `.kit/work/`에 있다. 그래서 세션이 끊겨도 이어서 할 수 있다.

- 아래 명령은 모두 `docs/v2/regression/P7-T1-doc-commands.md`에 실행 기록이 있다.
- 같은 흐름의 전체 출력 예시는 `docs/examples/v2-hitl.log`, 자동 테스트는 `tests/test_p6_e2e.py`다.
- 에이전트는 `task-approval`, `session-recovery`, `counterexample-hunter` 스킬을 보고 이 명령을 쓴다. 사람이 직접 써도 된다.

## 1. 승인 강제 수준

| 수준 | 무엇 | 켜는 법 |
|---|---|---|
| L0 | 정책 문구: 승인 없이 다음 Task로 가지 않는다 | 항상(`AGENTS.md`/`CLAUDE.md`) |
| L1 | 상태 기계: 의존 Task가 승인되지 않으면 `task start`가 거부한다(종료 코드 2). 터미널이 없으면 기본 승인 방식이 거부된다 | 항상 |
| L2 | 훅: 사용자의 답이 승인 단어뿐이면 승인을 기록하고, 에이전트가 승인 파일을 쓰지 못하게 막는다 | `kit install --agent … --hooks` |

L2는 완전한 보안 경계가 아니다. 셸로 우회할 수 있다. 승인 기록의 `by` 필드(`human-cli`, `human-hook`, `agent-recorded`)를 보면 누가 기록했는지 나중에 확인할 수 있다(`docs/SECURITY.md`).

## 2. 요구사항과 Task 만들기

```bash
kit req add REQ-001 --text "add returns the sum"
kit req add REQ-002 --text "div refuses a zero divisor"
kit req add REQ-003 --text "mean of a list" --priority should
kit task add T-1 --title "calc" --requires REQ-001 --requires REQ-002
kit task add T-2 --title "stats" --requires REQ-003 --depends-on T-1
kit task status
```

- 요구사항은 `TASK_BRIEF.md`에서 가져올 수도 있다: `kit req sync --brief TASK_BRIEF.md`. 브리프의 `## Requirements` 아래에 `- REQ-004 (should): report the median` 같은 줄을 둔다. 새 줄은 추가하고, 문구가 바뀐 줄은 개정한다.
- 우선순위 `must`(기본) 요구사항은 보고서 4절에 테스트 행이 있어야 제출된다.
- `--grade C` Task는 반례 기록도 있어야 제출된다(5절).

## 3. 진행과 제출

```bash
kit task start T-1
kit task subtask add T-1 "zero divisor"      # 선택: 승인이 필요 없는 하위 작업
kit task subtask done T-1.1
kit task report T-1                          # .kit/work/reports/T-1.md 템플릿(보고 형식 1~9절)
kit task submit T-1
```

- 보고서가 없거나 빈 템플릿이면 `submit`이 거부한다(종료 코드 2). 이유가 출력된다. 예: `no test row for must requirement REQ-001 in section 4`.
- 실행하지 않은 테스트는 4절 Status에 `NOT RUN: <사유>`로 적는다. 사유가 없으면 거부한다.

## 4. 테스트 증거로 4절 채우기

```bash
kit trace link TC-001 --req REQ-001 --locator tests/test_calc.py::test_add --case normal
kit trace link TC-002 --req REQ-002 --locator tests/test_calc.py::test_div_by_zero --case error
python -m pytest --junitxml=out/junit.xml
kit report tests --junit out/junit.xml --out .kit/work/reports/T-1-tests.md
kit trace check
```

- `report tests`는 JUnit XML(pytest, vitest, go-junit-report)과 `trace.json`의 연결로 4절 표를 만든다. 그 표의 행을 보고서 4절에 붙인다.
- 모든 연결 테스트가 통과하고 모든 요구사항에 테스트가 있어야 READY(0)다. 아직 테스트가 없는 요구사항(다음 Task 몫)이 있으면 PARTIAL(1)로 그 이름이 나온다.
- `trace check`는 테스트가 없는 must 요구사항, 개정된 요구사항을 아직 보는 테스트 같은 빈틈을 보여 준다(있으면 1).

## 5. 반례 (C 등급)

```bash
kit ce add CE-001 --function div --req REQ-002 --category boundary --origin black-box \
  --assumption "the divisor is never zero" --input "div(1, 0)" --would-catch "a ZeroDivisionError leak" \
  --expected "ZeroDivisionError"
kit ce accept CE-001
kit ce convert CE-001 --test TC-002
kit ce result CE-001 --result "PASS (TC-002)"
kit ce list
```

- 흐름: `PROPOSED` → `accept` / `reject --reason` / `needs-spec --question` → `ACCEPTED` → `convert --test` → `CONVERTED`.
- `accept`는 기대 결과(`--expected`)가 있는 반례만 받는다. 요구사항으로 기대 결과를 정할 수 없으면 추측하지 말고 `needs-spec CE-001 --question "…"`으로 사람에게 묻는다.
- `needs-spec`로 사람에게 물은 항목은 사람이 답한 뒤 `resolve --expected … --quote "<사람의 말>"`로 정한다.
- C 등급 Task는 그 요구사항의 반례 기록이 하나 이상 있고 `PROPOSED`가 남지 않아야 제출된다.
- Claude Code에서는 블랙박스 단계에 서브에이전트 `counterexample-blackbox`를 쓴다. 이 서브에이전트는 구현을 보지 않는다.

## 6. 승인

```bash
kit task approve T-1                                       # 사람이 터미널에서: Task ID를 다시 입력
kit task approve T-1 --by agent-recorded --evidence "승인"  # 에이전트가 사용자의 말을 기록
kit task request-changes T-1 --reason "add a test for -0.0"
```

- **기본(`human-cli`):** 터미널에서 Task ID를 다시 입력해야 한다. 터미널이 없으면 거부한다(종료 코드 2).
- **에이전트(`agent-recorded`):** 사용자가 대화에서 한 말을 `--evidence`로 남긴다. 기록에 에이전트가 남긴 것으로 표시된다. 훅(L2)이 켜진 작업 공간에서는 거부되고, 훅이 승인을 기록한다.
- 제출 뒤 보고서가 바뀌면 승인을 거부한다. 다시 제출해야 한다.
- 승인하면 `.kit/work/HANDOFF.md`가 새로 만들어진다. 승인된 상태만 담긴다: 마지막 승인 Task, 테스트 요약, 남은 위험, 다음 계획, 승인 이력.
- 작업 공간 루트의 `HANDOFF.md`는 사용자 파일이므로 읽지도 고치지도 않는다.

**훅이 있을 때:** 에이전트가 제출한 뒤 사용자가 `승인` 또는 `승인 T-1`만 답한다. 그러면 훅이 `by: human-hook`으로 기록한다. 다른 말이 섞이면 기록하지 않는다.

## 7. 세션 복구

```bash
kit recover save --note "mean() half done" --command "pytest tests" --tests "2 passed"
kit recover decide "use statistics.fmean for floats" --task T-2
kit recover
```

- `recover save`는 임시 상태(WIP)를 `.kit/work/wip.json`에 덮어쓴다. 승인된 상태가 아니다.
- `recover decide`는 결정을 `.kit/work/decisions.md`에 덧붙인다.
- 새 세션에서는 `kit recover`부터 실행한다. 다음을 **나눠서** 보여 준다.
  - 승인된 상태: 현재 Task, 마지막 승인, 승인 뒤 바뀐 파일, 테스트 요약, 위험, 다음 계획, 결정.
  - 임시 상태: WIP 메모, 마지막 명령, 마지막 테스트, 열린 오류.
- WIP를 남긴 Task가 그 뒤에 승인됐으면 `Out of date?`로 알려 준다.

## 8. 요구사항이 바뀌었을 때

```bash
kit req edit REQ-002 --text "div refuses zero and None divisors"
kit req impact REQ-002
```

- 문구를 바꾸면 개정 번호가 올라간다(`r2`). 이전 개정을 보던 테스트는 `Review:`로 나온다.
- `req impact`는 그 요구사항을 확인하는 테스트와 다시 볼 테스트를 보여 준다.

## 9. 파일

| 파일 | 내용 | 누가 쓰나 |
|---|---|---|
| `.kit/work/tasks.json` | Task 상태와 승인 기록 | `kit task`, 승인 훅 |
| `.kit/work/trace.json` | 요구사항, 테스트 연결 | `kit req`, `kit trace` |
| `.kit/work/counterexamples.json` | 반례 | `kit ce` |
| `.kit/work/reports/<Task>.md` | 완료 보고서 | 사람 또는 에이전트 |
| `.kit/work/HANDOFF.md` | 승인된 상태 요약 | 키트(손으로 고치지 않는다) |
| `.kit/work/wip.json`, `decisions.md` | 임시 상태, 결정 | `kit recover` |

종료 코드: 0 끝남, 1 경고(빈틈, 테스트 미통과, 복구 경고), 2 규칙에 따른 거부, 64 잘못된 인수, 65 상태 파일 손상.
