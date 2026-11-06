# ADR-018: 사용자(전역) 범위 설치 설계
- 상태: 승인(2026-11-05)
- 관련: D-18, REQ-USER-001/002/005, R-8, R-10
- 날짜: 2026-11-05

## 배경
검토자는 레포 하나로 어느 PC에서든 이 PC 수준의 전역 설정을 적용하고 싶어 한다. 대상은 Codex·Claude 스킬, 정책, MCP, 플러그인, OMX다. 전역 파일을 망가뜨리면 피해가 크다(R-8).

## 선택지
1. `install --scope user`로 opt-in한다: plan(diff) → TTY 확인 또는 `--yes` → 백업 → 키트가 소유한 구간·키만 수정.
2. 레포에서 전역 폴더로 심볼릭 링크를 건다(Windows 권한 문제가 있고, 사용자 파일을 덮어쓴다).
3. 설치 스크립트 없이 문서만 둔다.

## 결정
**선택지 1.** 대상과 방식:

| 대상 | 방식 |
|---|---|
| `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` | `hackathon-kit` 관리 구간(D-03). 결과 크기가 32 KiB에 가까우면 경고한다(R-10) |
| `~/.codex/config.toml` | 관리 구간에 MCP·플러그인을 선언한다. `projects.*`, `auth`, 앱이 관리하는 항목은 건드리지 않는다 |
| `~/.claude/settings.json` | D-05 소유 키(`enabledPlugins`, `extraKnownMarketplaces`, 키트가 정한 기본값) |
| `~/.codex/skills/<name>/` | 스킬 폴더 단위로 소유한다(Q5) |
| `~/.claude/skills/<name>/` | 스킬 폴더 단위로 소유한다 |
| `~/.codex/agents/*.toml`, `~/.codex/prompts/*` | OMX(REQ-USER-005). 파일 단위로 소유한다 |
| Claude 사용자 MCP(`~/.claude.json`) | **직접 쓰지 않는다.** 이 파일에는 세션 상태가 섞여 있다. 대신 `claude mcp add --scope user …` 명령을 출력만 한다 |

- 상태는 `~/.kit-state/manifest.json`, 백업은 `~/.kit-backups/<stamp>/`에 둔다.
- `uninstall --scope user`는 키트 소유 항목만 지우고, 백업에서 복구할 수 있다.
- 모든 테스트는 임시 HOME으로 격리한다(V-19).
- 실제 PC에 처음 적용하는 것은 검토자가 직접 한다.

## 근거
- 기존 프로젝트 범위 메커니즘(소유 구간, 해시, 백업)을 그대로 재사용한다.
- `~/.claude.json`은 Claude가 실행 중에 고쳐 쓰므로 직접 쓰면 경쟁 상태가 생긴다.

## 결과와 위험
- 위험: OMX 같은 외부 설치 도구와 같은 파일을 소유하면 충돌한다 → OMX가 직접 설치한 흔적이 있으면 CONFLICT로 보고하고 덮어쓰지 않는다.

## 되돌리는 방법
`uninstall --scope user`를 실행하거나 `~/.kit-backups/<stamp>/`에서 복원한다.
