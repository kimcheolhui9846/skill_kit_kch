# ADR-003: 관리 구간 마커 이름
- 상태: 승인(Q4)
- 관련: D-03, Q4
- 날짜: 2026-11-05

## 배경
기존 마커는 `<!-- hackathon-kit:begin/end -->`(AGENTS.md)와 `# hackathon-kit:begin/end`(config.toml)다. 이제 키트가 해커톤 전용이 아니라서 이름이 어색하다.

## 선택지
1. 마커를 바꾸지 않는다.
2. 새 마커 `skill-kit`을 쓰고, 두 마커를 모두 인식하는 코드와 `migrate` 명령을 둔다.

## 결정
**선택지 1(검토자 결정 Q4, 2026-11-05).** 새 파일에도 `hackathon-kit` 마커를 쓴다: `CLAUDE.md`, user 범위의 `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, `~/.codex/config.toml`. `migrate` 명령은 만들지 않는다.

## 근거
두 마커가 공존하면 한 파일에 구간이 두 개 생길 위험이 있고, 마이그레이션 코드도 필요해진다. 마커를 유지하는 비용은 이름이 어색하다는 것뿐이다.

## 결과와 위험
- 05_CLI_SPEC에서 원문 §P2-T5의 `migrate`를 뺀다.
- 위험: 없음(기존 인식 로직 `kit/agentsmd.py:41-64`를 재사용).

## 되돌리는 방법
나중에 바꾸려면 선택지 2를 새 ADR로 추가한다.
