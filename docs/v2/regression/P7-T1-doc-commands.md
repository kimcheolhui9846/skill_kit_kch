# P7-T1 문서 명령 실행 기록

<!-- devtools/run_doc_commands.py가 만든다. 손으로 고치지 않는다. -->

- 환경: Windows 11, Python 3.12.10
- 방식: 명령마다 새 `python -I run_kit.py` 프로세스, 터미널 없음, 임시 작업 공간과 임시 HOME(`<home>`), 네트워크 없음. 문서의 설치 명령 중 네트워크를 쓸 수 있는 것은 `--offline`을 붙여 실행했다.
- 결과: 95개 실행, 기대와 다른 종료 코드 0개.

| 문서 | 명령 | 기대 | 실제 | Status 줄 | 판정 |
|---|---|---|---|---|---|
| README.md | `bash ../skill_kit_kch/bootstrap.sh install --agent codex (+ --offline)` | 0 | 0 | READY | PASS |
| README.md | `bash ../skill_kit_kch/bootstrap.sh install --agent claude (+ --offline)` | 0 | 0 | READY | PASS |
| README.md | `bash ../skill_kit_kch/bootstrap.sh install --agent both (+ --offline)` | 0 | 0 | READY | PASS |
| README.md | `..\skill_kit_kch\bootstrap.ps1 install --agent both (+ --offline)` | 0 | 0 | READY | PASS |
| README.md | `kit install --agent both` | 0 | 0 | READY | PASS |
| README.md | `kit help` | 0 | 0 | - | PASS |
| INSTALL.md | `kit plan --agent both` | 0 | 0 | - | PASS |
| INSTALL.md | `kit install --agent both --dry-run` | 0 | 0 | - | PASS |
| INSTALL.md | `kit install --agent codex` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit install --agent claude` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit install --agent both` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit verify --agent both` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit update --agent both --dry-run` | 0 | 0 | - | PASS |
| INSTALL.md | `kit update --agent both` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit uninstall --agent both --dry-run` | 0 | 0 | - | PASS |
| INSTALL.md | `kit uninstall --agent both` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit install --agent codex --offline` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit restore --backup 20261108-142230 --dry-run` | 0 | 0 | - | PASS |
| INSTALL.md | `kit restore --backup 20261108-142230` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit restore --agent codex --backup 20261108-142230` | 64 | 64 | usage error | PASS |
| INSTALL.md | `kit install --agent both --offline` | 0 | 0 | READY | PASS |
| INSTALL.md | `kit doctor` | 0 | 0 | - | PASS |
| INSTALL.md | `kit profiles list` | 0 | 0 | - | PASS |
| INSTALL.md | `kit profiles show hackathon --agent codex` | 0 | 0 | - | PASS |
| INSTALL.md | `kit version` | 0 | 0 | - | PASS |
| INSTALL.md | `kit install --agent both --scope user --dry-run` | 0 | 0 | - | PASS |
| INSTALL.md | `kit install --agent both --scope user` | 64 | 64 | usage error | PASS |
| INSTALL.md | `bash <kit>/bootstrap.sh install --agent both --offline` | 0 | 0 | READY | PASS |
| INSTALL.md | `powershell -ExecutionPolicy Bypass -File <kit>\bootstrap.ps1 install --agent both --offline` | 0 | 0 | READY | PASS |
| CODEX.md | `kit install --agent codex` | 0 | 0 | READY | PASS |
| CODEX.md | `kit install --agent codex --policy restricted` | 0 | 0 | READY | PASS |
| CODEX.md | `kit install --agent codex --mcp context7 --hooks` | 0 | 0 | READY | PASS |
| CODEX.md | `kit install --agent codex --scope user --dry-run` | 0 | 0 | - | PASS |
| CLAUDE_CODE.md | `kit install --agent claude` | 0 | 0 | READY | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --mcp context7 --hooks` | 0 | 0 | READY | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --scope user --dry-run` | 0 | 0 | - | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --scope user --hooks --dry-run` | 64 | 64 | usage error | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --scope user --plugin security-guidance --dry-run` | 64 | 64 | usage error | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --plugin security-guidance --dry-run` | 0 | 0 | - | PASS |
| CLAUDE_CODE.md | `kit install --agent claude --hooks` | 0 | 0 | READY | PASS |
| CLAUDE_CODE.md | `kit uninstall --agent claude` | 0 | 0 | READY | PASS |
| HITL_WORKFLOW.md | `kit req add REQ-001 --text "add returns the sum"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit req add REQ-002 --text "div refuses a zero divisor"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit req add REQ-003 --text "mean of a list" --priority should` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task add T-1 --title "calc" --requires REQ-001 --requires REQ-002` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task add T-2 --title "stats" --requires REQ-003 --depends-on T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task status` | 0 | 0 | READY | PASS |
| HITL_WORKFLOW.md | `kit req sync --brief TASK_BRIEF.md` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task start T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task subtask add T-1 "zero divisor"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task subtask done T-1.1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task submit T-1` | 2 | 2 | BLOCKED | PASS |
| HITL_WORKFLOW.md | `kit task report T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task submit T-1` | 2 | 2 | BLOCKED | PASS |
| HITL_WORKFLOW.md | `kit trace link TC-001 --req REQ-001 --locator tests/test_calc.py::test_add --case normal` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit trace link TC-002 --req REQ-002 --locator tests/test_calc.py::test_div_by_zero --case error` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `python -m pytest --junitxml=out/junit.xml` | 0 | 0 | - | PASS |
| HITL_WORKFLOW.md | `kit report tests --junit out/junit.xml --out .kit/work/reports/T-1-tests.md` | 1 | 1 | PARTIAL | PASS |
| HITL_WORKFLOW.md | `kit trace check` | 1 | 1 | GAPS | PASS |
| HITL_WORKFLOW.md | `kit ce add CE-001 --function div --req REQ-002 --category boundary --origin black-box --assumption "the divisor is never zero" --input "div(1, 0)" --would-catch "a ZeroDivisionError leak" --expected "ZeroDivisionError"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce accept CE-001` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce convert CE-001 --test TC-002` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce result CE-001 --result "PASS (TC-002)"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce add CE-002 --function div --req REQ-002 --category type --origin black-box --assumption "the divisor is a number" --input "div(1, None)" --would-catch "a TypeError leak"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce accept CE-002` | 2 | 2 | BLOCKED | PASS |
| HITL_WORKFLOW.md | `kit ce needs-spec CE-002 --question "what should div(1, None) do?"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce resolve CE-002 --expected "ValueError" --quote "None은 ValueError로"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit ce list` | 0 | 0 | READY | PASS |
| HITL_WORKFLOW.md | `kit task submit T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task request-changes T-1 --reason "add a test for -0.0"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task start T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task submit T-1` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task approve T-1` | 2 | 2 | BLOCKED | PASS |
| HITL_WORKFLOW.md | `kit task approve T-1 --by agent-recorded --evidence "승인"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit task start T-2` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit recover save --note "mean() half done" --command "pytest tests" --tests "2 passed"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit recover decide "use statistics.fmean for floats" --task T-2` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit recover` | 0 | 0 | READY | PASS |
| HITL_WORKFLOW.md | `kit req edit REQ-002 --text "div refuses zero and None divisors"` | 0 | 0 | DONE | PASS |
| HITL_WORKFLOW.md | `kit req impact REQ-002` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit --offline` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit --profile python --offline --dry-run` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit --help` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit help` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit plan --agent codex --policy restricted --profile core` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit verify --agent codex` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit doctor` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit plan --agent codex --offline` | 0 | 0 | - | PASS |
| MIGRATION_V1_TO_V2.md | `kit install --agent codex --offline` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit verify --agent codex --offline` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit uninstall --agent codex` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit --offline` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit --offline` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit install --agent codex --policy restricted --profile core` | 0 | 0 | READY | PASS |
| MIGRATION_V1_TO_V2.md | `kit uninstall --agent codex` | 0 | 0 | READY | PASS |
