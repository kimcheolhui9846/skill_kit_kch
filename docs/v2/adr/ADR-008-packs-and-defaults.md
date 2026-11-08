# ADR-008: 새 스킬을 기존 프로필에 넣을지와 새 경로의 기본 프로필
- 상태: 승인(2026-11-05)
- 관련: D-08, REQ-COMPAT-003, REQ-SKILL-001
- 날짜: 2026-11-05

## 배경
기존 5개 프로필(core, python, web, data, full)의 설치 내용은 바뀌면 안 된다.

## 선택지
1. 새 스킬은 팩으로만 묶는다(`hitl`, `verify-plus`, `launch`). 신규 프로필(`fullstack`, `ai-research`, `hackathon`)은 팩을 포함한다.
2. 기존 프로필에 직접 추가한다(REQ-COMPAT-003 위반).

## 결정
**선택지 1.**
- 새 경로에서 `--profile`을 생략했을 때의 기본값으로 **`core,hitl`**이다(검토자 결정, 2026-11-05).
- `launch-compliance-check`는 `launch` 팩에 넣고, 새 경로의 `web`·`fullstack` 조합에 포함한다(REQ-SKILL-001).
- 사용자 목록에서 채택한 외부 스킬은 P4-T3 평가 결과에 따라 팩에 배정한다(REQ-SRC-007).

## 개정 (2026-11-08)
검토자가 구현을 그대로 두기로 정했다. 위 결정 중 "새 스킬은 팩으로만 묶는다"를 다음과 같이 고친다.
- `task-approval`, `session-recovery`는 standard 정책의 `core` 팩에 들어간다(`catalog/skills.json`). 그래서 `hitl`을 고르지 않는 프로필(`python`, `web`, `data`)도 standard 정책에서는 이 두 스킬을 받는다.
- `hitl` 팩은 스킬을 나열하지 않는다(`profiles/packs/hitl.json`의 `skills`가 비어 있다). 이 팩이 맡는 것은 `kit task/req/trace/report/ce/recover` 명령과 정책 문구다.
- restricted 정책의 설치 내용은 바뀌지 않는다.
- 기본값 `core,hitl`은 그대로다.

## 근거
- 기존 프로필 파일을 건드리지 않으면 REQ-COMPAT-003이 구조적으로 보장된다.
- `core,hitl`을 제안하는 이유: v2의 핵심 기능이 HITL이고, 새 경로를 쓰는 사람은 v2 기능을 기대한다.

## 결과와 위험
- 테스트: 기존 5개 프로필의 설치 트리가 골든과 같은지.

## 되돌리는 방법
기본값 상수 하나만 바꾸면 된다.
