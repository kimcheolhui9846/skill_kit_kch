# ADR-010: 플러그인 처리 범위
- 상태: 승인(2026-11-05)
- 관련: D-10
- 날짜: 2026-11-05

## 배경
Codex(`[plugins."x@m"] enabled`, 루트 `plugin.json`)와 Claude(`enabledPlugins`, `extraKnownMarketplaces`) 모두 설정 파일로 플러그인을 선언하는 공식 경로가 있다(02 매트릭스).

## 선택지
1. 선언과 안내만 한다. 기본은 비활성이고, 고위험 플러그인은 선언도 opt-in이다.
2. 키트가 플러그인을 직접 설치한다.

## 결정
**선택지 1.**
- 프로젝트 범위:
  - Claude: `.claude/settings.json`의 `extraKnownMarketplaces`·`enabledPlugins`를 D-05의 소유 키로 다룬다.
  - Codex: `.codex/config.toml` 관리 구간에 둔다.
- user 범위(D-18)도 같은 방식이다.
- 실제 설치는 사용자가 에이전트 안에서(`/plugin`) 한다.
- 고위험 플러그인(`computer-use` 등)은 카탈로그에 `enabled_by_default: false`로 고정하고 테스트로 강제한다.

## 근거
원문 권장안이고, 두 에이전트 모두 공식 선언 경로가 있다.

## 결과와 위험
- 위험: 선언만으로는 설치되지 않아 사용자가 혼동할 수 있다 → 보고서의 다음 행동 안내에 설치 명령을 출력한다.

## 되돌리는 방법
선언 키를 지우면 된다(D-05의 제거 절차).
