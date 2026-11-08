# 호환성

1부는 v2 전체의 지원 환경이다. 2부는 v1 설치기 문서를 그대로 둔 것이다. 에이전트별 경로와 공식 문서 근거는 `docs/v2/02_COMPATIBILITY_MATRIX.md`에 있다.

# 1부. v2 지원 환경

| 항목 | 요구 | 확인 수준 |
|---|---|---|
| Python | 3.9 이상, 표준 라이브러리만 | 3.12(Windows), 3.11·3.14(WSL Ubuntu)에서 전체 테스트. **실제 3.9.25**(WSL)에서 전체 테스트 1397개 통과(P6-T4) |
| TOML 감사·비교 | Python 3.11+(`tomllib`) | 3.9~3.10은 줄 단위 검사. 위반은 FAIL, 못 찾으면 `UNVERIFIED`(설계) |
| Windows | Windows 11, PowerShell 5.1 | 전체 테스트와 문서 명령 실행. 한국어 로캘(cp949) 콘솔에서 실행(P6-T4) |
| PowerShell 7 | | **미검증**. 검토자 점검표 `docs/v2/WINDOWS_MANUAL_CHECK.md` |
| Linux | bash 3.2+ | WSL2 Ubuntu 26.04에서 전체 테스트와 CLI(P6-T4). 실제 Linux 기기와 macOS는 **미검증** |
| Codex | codex-cli 0.166.0 | 파일 경로는 공식 문서(VERIFIED-DOC). 승인 훅은 실제 실행(M-05). 스킬·MCP 로드는 검토자 점검표 `docs/v2/AGENT_LOAD_CHECK.md`(**UNVERIFIED**) |
| Claude Code | 2.1.319 | Codex와 같음 |
| Node/npx | MCP에만 필요 | 없으면 MCP 연결 확인이 FAIL(선택 항목), 나머지는 정상 |
| git | 세션 복구의 "바뀐 파일"에 쓰면 정확하다 | 없으면 파일 해시로 비교한다 |

## 에이전트별 차이

| | Codex | Claude Code |
|---|---|---|
| 정책 파일 | `AGENTS.md` | `CLAUDE.md`(있으면 `AGENTS.md`는 읽지 않음) |
| 프로젝트 스킬 | `.agents/skills/` | `.claude/skills/` |
| 프로젝트 MCP | `.codex/config.toml`, 신뢰한 프로젝트만 | `.mcp.json`, 대화형 세션에서 승인 |
| 훅 | `.codex/hooks.json`, 신뢰와 `/hooks` 검토 필요, 보조 수단 | `.claude/settings.json`, 폴더 신뢰 필요 |
| 사용자 스킬 | `~/.codex/skills`(문서에 없는 호환 동작, 0.166.0에서 확인) | `~/.claude/skills` |

## 플랫폼별 주의

- **줄 끝:** 저장소는 `.gitattributes`로 LF를 지정한다. 키트는 Windows와 Linux에서 같은 순서와 같은 바이트로 파일을 쓴다. 파일 정렬 순서도 플랫폼에 상관없이 같다(P6-T4에서 고침).
- **cp949 콘솔:** 명령은 실패하지 않는다. cp949에 없는 문자는 화면에만 `?`로 보인다. 파일은 항상 UTF-8이다.
- **PowerShell 5.1:** BOM이 없는 `.ps1`을 cp949로 읽는다. `bootstrap.ps1`은 ASCII만 쓰고, 테스트가 이를 지킨다.
- **심볼릭 링크:** 키트는 링크를 만들지 않는다. Windows에서 링크 관련 테스트 2개는 권한이 없어 건너뛰고, Linux에서는 실행된다.

# 2부. v1 설치기

## 지원 범위

| 항목 | 요구 | 비고 |
|---|---|---|
| Python | 3.9+ | 없으면 셸 전용 모드(아래) |
| TOML 파싱, 설정 감사 | Python 3.11+ (`tomllib`) | 3.9~3.10에서는 줄 단위 검사로 위험 항목을 FAIL로 잡고, 못 찾으면 `UNVERIFIED` |
| bash | 3.2+ | `bootstrap.sh` |
| PowerShell | Windows PowerShell 5.1+ | `bootstrap.ps1` |
| Node/npx | MCP에만 필요 | 없으면 MCP 항목이 FAIL(선택), 나머지는 정상 |
| Codex | codex-cli 0.165.0에서 확인 | `codex mcp list --json` 형식 |

Python 탐색 순서는 `$KIT_PYTHON`, `python3`, `python`, (Windows) `py -3`이다. `py -3`은 `bootstrap.ps1`만 시도한다. 3.9 미만이면 없는 것으로 본다.

## Windows의 bash

Git Bash의 `bash`와 WSL의 `bash`는 다르다. `bash`가 어느 쪽으로 잡히는지에 따라 보이는 경로와 도구가 달라질 수 있다. Windows에서는 PowerShell 진입점(`bootstrap.ps1`) 또는 Git Bash를 쓴다. 로컬에서는 Git Bash로 확인했다(`docs/TEST_REPORT.md`).

Windows에서 MCP 점검은 `npx.cmd`(cmd.exe → node)를 시작한다. 서버가 stdin 종료를 무시하면 점검 뒤에 node 프로세스가 남을 수 있다. 작업 관리자에서 직접 종료한다. 핸드셰이크는 최대 120초 기다리고, 종료 시 5초 유예를 둔다.

## MCP 버전 선택

`@modelcontextprotocol/server-sequential-thinking`을 `2026.8.31`로 고정했다. 2.0.0(2026-10-19)은 node 24 이상이 필요하고, 2026.8.31은 `engines`를 선언하지 않아 오래된 시험 환경에서도 시작할 가능성이 높다.

## Codex 신뢰

Codex는 `.codex/config.toml`을 신뢰된 프로젝트에서만 로드한다. 신뢰하지 않으면 MCP가 보이지 않으며 키트는 `codex-mcp:sequential-thinking`을 `UNVERIFIED`로 보고한다. 이는 실패가 아니다. 프로젝트를 신뢰한 뒤 Codex에서 `/mcp`로 확인한다.

`codex mcp list --json`은 JSON 배열(각 원소에 `name`)을 출력하며, 키트는 대상 디렉터리에서 이를 실행해 서버 이름을 찾는다.

## 셸 전용 모드

Python 3.9+가 없으면 어떤 프로필을 고르든 `AGENTS.md`와 Skill만 설치한다. 도구 설치, MCP, 검증, 로그, 백업은 없다. 종료 코드는 1(`PARTIAL`)이다. 자세한 한계는 `README.md`의 "셸 전용 모드의 한계"를 본다.
