# 설치 가이드

키트를 작업 공간에 설치하고, 미리 보고, 검증하고, 업데이트하고, 제거하고, 되돌리는 방법이다. 에이전트별 내용은 `CODEX.md`, `CLAUDE_CODE.md`에 있다.

## 0. `kit`이라는 이름

아래의 `kit`은 키트 폴더의 진입점 셋 중 하나다. 셋 다 인수를 그대로 넘긴다.

| 진입점 | 예 (키트를 작업 공간의 형제 폴더 `../skill_kit_kch`에 받은 경우) |
|---|---|
| Python | `python ../skill_kit_kch/run_kit.py install --agent both` |
| bash (Linux, macOS, Git Bash) | `bash ../skill_kit_kch/bootstrap.sh install --agent both` |
| PowerShell | `..\skill_kit_kch\bootstrap.ps1 install --agent both` |

- 키트는 Python 3.9 이상의 표준 라이브러리만 쓴다. 설치할 패키지가 없다.
- 명령은 작업 공간에서 실행한다. 다른 곳에서 실행하려면 `--target <작업 공간>`을 준다.
- 대상이 키트 폴더 자신이면 거부한다(종료 코드 65).
- 명령 없이 실행하면(`bootstrap.sh`, `bootstrap.ps1 --profile python` 등) v1 설치기가 그대로 동작한다. `MIGRATION_V1_TO_V2.md`를 본다.

## 1. 키트 받기

```bash
git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch ../skill_kit_kch
```

**미검증(P7-T1 자동 기록 밖):**
- 네트워크가 필요한 명령이라 문서 명령 기록(`P7-T1-doc-commands.md`)에는 없다.
- v2를 `main`에 병합한 뒤(2026-11-09, PR #10) 직접 clone해서 `install --agent both`와 `verify`가 READY인 것을 확인했다.
- v1의 같은 명령은 `docs/TEST_REPORT.md`(v1)에 실행 기록이 있다.

## 2. 미리 보기

쓰기 전에 무엇이 바뀌는지 본다. 아무것도 쓰지 않는다.

```bash
kit plan --agent both
kit install --agent both --dry-run      # 같은 결과
```

- 출력은 파일마다 `CREATE`/`UPDATE`/`APPEND`/`UNCHANGED`/`CONFLICT`로 나온다. 끝에 `Summary:`와 `DRY RUN: nothing was written.`이 나온다.
- 예시: `docs/examples/v2-plan.log`.

## 3. 설치

```bash
kit install --agent codex      # AGENTS.md, .agents/skills/, .codex/config.toml
kit install --agent claude     # CLAUDE.md, .claude/skills/, .mcp.json
kit install --agent both       # 둘 다. 하나라도 실패하면 둘 다 되돌린다
```

| 옵션 | 뜻 | 기본값 |
|---|---|---|
| `--profile a[,b]` | 프로필과 팩 조합. 목록은 `kit profiles list`, 설치될 스킬은 `kit profiles show`나 `docs/CATALOG.md` | `core,hitl` |
| `--policy standard\|restricted` | `restricted`는 v1과 같은 스킬 11개(시험용). `standard`는 외부 스킬 포함 17개 | `standard` |
| `--offline` | 네트워크를 쓰지 않는다. 네트워크가 필요한 항목은 `SKIPPED` | 끔 |
| `--yes` | 네트워크 사용과 user 범위 변경을 묻지 않고 허용한다. 터미널이 없으면 이것이 있어야 그런 작업을 한다 | 끔 |
| `--mcp NAME` | 기본으로 꺼진 MCP 서버를 켠다(예: `context7`) | 없음 |
| `--no-mcp` | MCP를 등록하지 않는다 | 끔 |
| `--hooks` | 승인 기록 훅(opt-in, `HITL_WORKFLOW.md`) | 끔 |
| `--json` / `--report-json FILE` | 기계가 읽는 결과 | 끔 |

**설치 결과:**
- 보고서 끝의 `Status:`가 `READY`면 끝이다. 예시: `docs/examples/v2-install-both.log`.
- `Load UNVERIFIED`는 정상이다. 에이전트가 파일을 실제로 읽었는지는 에이전트 안에서만 볼 수 있다(`docs/v2/AGENT_LOAD_CHECK.md`).

**기존 파일:**
- 기존 `AGENTS.md`/`CLAUDE.md`는 덮어쓰지 않는다. 키트 구간(`<!-- hackathon-kit:begin -->` … `end`)만 쓴다.
- 고치기 전 원본은 `.kit/backups/<시각>/`에 남는다.
- 사용자가 고친 키트 파일은 `CONFLICT`로 두고 건드리지 않는다.

## 4. 검증

```bash
kit verify --agent both
```

- 쓰지 않는다. 키트가 쓴 파일이 기록과 같은지, 설정 감사가 통과하는지 본다. 예시: `docs/examples/v2-verify.log`.
- install에서 `--mcp`로 켠 서버는 기록에 남는다. 그래서 verify에 다시 줄 필요가 없다.

## 5. 업데이트

키트를 새 버전으로 받은 뒤 실행한다.

```bash
kit update --agent both --dry-run
kit update --agent both
```

- 키트가 쓴 것만 이 키트 버전으로 다시 쓴다. 프로필에서 빠진 키트 항목은 지운다.
- 사용자가 고친 파일은 `CONFLICT`로 두고, 그 뒤로는 사용자 것으로 본다.
- `update`는 `--profile`/`--policy`를 받지 않는다. 설치 때 고른 것을 그대로 쓴다.
- 프로필이나 정책을 바꾸려면 새 값으로 `install`을 다시 한다. 이전 설치에 있고 새 선택에 없는 키트 항목은 `update`와 같은 규칙으로 정리한다(그대로인 것은 백업 뒤 지우고, 고친 것은 `CONFLICT`로 남긴다). 미리 보려면 같은 값으로 `kit plan`을 실행한다.

## 6. 제거

```bash
kit uninstall --agent both --dry-run
kit uninstall --agent both
```

- 키트가 쓴 파일 중 내용이 기록과 같은 것만 지운다.
- `AGENTS.md`/`CLAUDE.md`는 키트 구간만 지운다. 키트 구간만 남아 있던 파일은 파일째 지운다.
- 사용자가 고친 파일은 `CONFLICT ... left in place`로 남긴다. 이 경우 `Status: BLOCKED`(종료 코드 2)로 끝나므로, 그 파일은 직접 지운다.
- 지우기 전 내용은 `.kit/backups/<시각>/`에 남는다. 출력의 `Backups:` 줄에 되돌리는 명령이 나온다. 예시: `docs/examples/v2-uninstall.log`.
- `.kit/` 폴더(작업 기록, 백업, 로그)는 지우지 않는다.

## 7. 백업에서 되돌리기

```bash
kit restore --backup 20261108-110245 --dry-run
kit restore --backup 20261108-110245
```

- `--backup`에는 `.kit/backups/` 아래 폴더 이름을 준다. `--agent`는 받지 않는다(종료 코드 64).
- 되돌리기 전의 파일도 새 백업으로 먼저 남긴다(`Saved first:` 줄).
- 끝나면 `kit verify --agent ...`로 상태를 다시 본다.

## 8. 오프라인

```bash
kit install --agent both --offline
```

- 네트워크를 전혀 쓰지 않는다. 도구 설치, MCP 연결 확인, 플러그인 설치는 `SKIPPED`다. 예시: `docs/examples/offline.log`(v1), `v2-install-codex.log`.
- `--offline` 없이 네트워크가 필요한 일이 있으면 키트가 먼저 묻는다. 터미널이 없으면 `--yes`가 없는 한 하지 않는다. 무엇을 받는지는 `docs/SECURITY.md`를 본다.

## 9. 상태 진단과 프로필

```bash
kit doctor
kit profiles list
kit profiles show hackathon --agent codex
kit version
```

- `doctor`: 이 PC에 어떤 에이전트 CLI가 있는지, 이 작업 공간에 키트가 무엇을 설치했는지(v1 흔적 포함) 보여 주고 다음 명령을 추천한다. 쓰지 않는다.
- `profiles show a[,b] [--agent A] [--policy standard|restricted]`: 그 프로필·에이전트·정책으로 `install`/`plan`이 **실제로 설치하는** 스킬을 보여 준다. 정책과 카탈로그를 적용한 결과이며 planner와 같은 코드로 계산한다(대체된 스킬은 `replaced: 옛 이름 -> 새 이름`, 빠진 스킬은 `skipped: 이름 (이유)` 줄로 따로 보인다). `--policy`를 빼면 `install`과 같은 기본값(프로필이 정하지 않으면 `standard`)을 쓰고, `Policy:` 줄에 실제로 쓴 정책을 적는다. Tools와 MCP 줄은 프로필 파일의 목록이다(MCP 카탈로그 필터는 `kit plan`에서 본다). 쓰지 않는다.

## 10. 사용자(홈) 범위

```bash
kit install --agent both --scope user --dry-run
kit install --agent both --scope user --yes
```

- 작업 공간이 아니라 `~/.codex`, `~/.claude`에 설치한다. 저장소의 `user/` 스냅숏, Codex의 OMX 스킬, 프로필의 키트 스킬이 들어간다.
- 쓰기 전에 꼭 `--dry-run`으로 diff를 본다. 터미널에서는 확인을 묻고, 터미널이 없으면 `--yes`가 있어야 한다(없으면 64).
- 백업은 `~/.kit-backups/`에 남는다.
- Claude Code의 사용자 MCP는 `~/.claude.json`을 고치지 않는다. 대신 `claude mcp add --scope user …` 명령을 출력하므로 직접 실행한다.

**미검증(P7-T1):** `--yes`로 실제 홈에 쓰는 명령은 이번에 실행하지 않았다. 임시 HOME에서는 `--dry-run`과 `--yes` 없는 거부(64)만 실행했다. 이 PC의 실제 적용은 검토자 작업 M-06이다.

## 11. Windows와 Linux

| | Windows | Linux / macOS |
|---|---|---|
| 진입점 | `bootstrap.ps1`(Windows PowerShell 5.1) 또는 `python run_kit.py` | `bootstrap.sh`(bash 3.2+) 또는 `python3 run_kit.py` |
| 실행 정책 | `.ps1`이 막히면 그 프로세스에만 `powershell -ExecutionPolicy Bypass -File ..\skill_kit_kch\bootstrap.ps1 install --agent both`. 전역 정책은 바꾸지 않는다 | 해당 없음 |
| 한글 콘솔(cp949) | 명령은 실패하지 않는다. cp949에 없는 문자는 화면에만 `?`로 보이고 파일에는 그대로 남는다(`docs/v2/WINDOWS_MANUAL_CHECK.md`) | 해당 없음 |
| 확인 | Windows 11, PowerShell 5.1, Python 3.12에서 전체 테스트와 이 문서의 명령 실행 | WSL2 Ubuntu에서 전체 테스트와 install·verify·task·uninstall·`bootstrap.sh` 실행(P6-T4), Python 3.9 포함 |

- PowerShell 7과 실제(WSL이 아닌) Linux 기기는 **미검증**이다(`docs/v2/regression/P6-T4-platform.md`).
- 이 문서의 나머지 명령은 Windows에서 Python 진입점과 Git Bash로 실행했다(`docs/v2/regression/P7-T1-doc-commands.md`).

## 12. 종료 코드

| 코드 | 상태 | 뜻 |
|---|---|---|
| 0 | READY | 끝남(미리 보기 포함) |
| 1 | PARTIAL | 필수 항목은 정상, 선택 항목 일부 실패 |
| 2 | BLOCKED | 필수 항목 실패, 규칙에 따른 거부, 사람이 판단할 충돌 |
| 64 | | 잘못된 인수 |
| 65 | | 대상 폴더가 없거나 키트 폴더 자신 |
