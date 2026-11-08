# v1에서 v2로 옮기기

## 1. 바뀌지 않는 것

**명령 없이 부르는 v1 사용법은 그대로 동작한다.**

```bash
kit --offline
kit --profile python --offline --dry-run
kit --help
```

- `bootstrap.sh`, `bootstrap.ps1`, `run_kit.py`를 명령 없이(옵션만 주거나 아무것도 없이) 부르면 v1 설치기가 돈다.
- v1 설치기는 Codex 전용이고, 스킬 11개, `restricted` 정책이다.
- 결과 트리와 보고서는 v1과 바이트 단위로 같다. 골든 테스트 `tests/golden/`가 매번 확인한다.
- `kit --help`의 출력도 v1 그대로다. 새 명령의 도움말은 `kit help`다.
- 시험 당일 절차(README의 "시험 당일 설치")도 그대로 쓸 수 있다.

**호환되는 것:**
- 마커가 같다. `AGENTS.md`의 `<!-- hackathon-kit:begin -->` … `end`, `.codex/config.toml`의 `# hackathon-kit:begin` … `end`를 v2도 그대로 쓴다.
- v1의 상태 파일 `.kit/state.json`을 v2도 읽는다.
- 종료 코드(0, 1, 2, 64, 65)가 같다.

## 2. 달라진 것

| | v1 | v2 (명령이 있는 호출) |
|---|---|---|
| 에이전트 | Codex | Codex, Claude Code, 둘 다(`--agent`) |
| 기본 정책 | restricted(스킬 11개) | standard(스킬 17개: 외부 스킬 포함, `tdd-automator`→`test-driven-development`, `submission-validator`→`verification-before-completion`) |
| 설치 기록 | `.kit/state.json` | `.kit/state/install-manifest.json`(에이전트별 소유 항목) |
| 수명 주기 | 설치, 검증 | 설치, 미리 보기, 검증, 업데이트, 제거, 백업 복원, 진단 |
| 작업 흐름 | 없음 | Task 승인, 요구사항 추적, 테스트 보고, 반례, 세션 복구(`HITL_WORKFLOW.md`) |
| 확장 | 없음 | MCP·플러그인 카탈로그(opt-in), GitHub 스킬 추가(`kit source add`), user 범위 |

**v1 옵션과 같은 뜻의 v2 명령:**

| v1 | v2 |
|---|---|
| `kit` | `kit install --agent codex --policy restricted --profile core` |
| `kit --dry-run` | `kit plan --agent codex --policy restricted --profile core` |
| `kit --verify-only` | `kit verify --agent codex` |
| `kit --offline`, `--no-mcp`, `--verbose`, `--target D` | 같은 옵션을 v2 명령에 붙인다 |

- v2의 보고서는 에이전트별 구간으로 나와서 v1 보고서와 글자까지 같지는 않다.
- 설치되는 파일은 같다. `migrate` 명령은 없다(ADR-003). 마커가 같아서 옮길 것이 없기 때문이다.

## 3. 옮기는 절차

v1이 설치된 작업 공간에서 실행한다.

```bash
kit doctor                          # Legacy state: yes (.kit/state.json) 가 보인다
kit plan --agent codex --offline    # v1에서 지워질 파일이 REMOVE 줄로 보인다
kit install --agent codex --offline # 또는 --agent both, --policy restricted
kit verify --agent codex --offline
```

- `install`은 v1 기록(`.kit/state.json`)을 읽고, 새 계획에 없는 v1 파일을 정리한다. standard에서는 `tdd-automator`, `submission-validator`와 `systematic-debugging/examples/example.md`가 대상이다(standard가 대체 스킬을 설치한다).
  - 내용이 v1이 쓴 그대로인 파일만 지운다. 지우기 전에 `.kit/backups/<시각>/`에 백업한다.
  - 사용자가 고친 파일은 지우지 않고 `CONFLICT`(`stale:<경로>`)로 보고한다. 이때 결과는 PARTIAL(1)이다.
  - 설치 보고서에 `removed (no longer in the profile): N item(s)` 줄이 나온다.
- **v1과 같은 스킬을 원하면** `--policy restricted --profile core`로 설치한다. 스킬 11개가 같아서 지우는 파일이 없다.
- 2026-11-08 이전 키트는 이 정리를 하지 않았다. 그 키트로 v1 위에 standard를 설치했다면, 남은 `tdd-automator`, `submission-validator` 폴더는 기록 밖에 있으므로 직접 지운다.

## 4. 되돌리기

```bash
kit uninstall --agent codex    # v2가 쓴 것을 지운다
kit --offline                  # v1 설치기로 다시 설치
```

- 특정 시점의 파일로 돌리려면 `kit restore --backup <시각>`을 쓴다(`INSTALL.md` 7절).
- `.kit/work/`(Task, 추적, 반례 기록)는 `uninstall`이 지우지 않는다. v1 설치기는 이 파일을 쓰지도 읽지도 않는다.

이 문서의 명령은 모두 `docs/v2/regression/P7-T1-doc-commands.md`에 실행 기록이 있다.
