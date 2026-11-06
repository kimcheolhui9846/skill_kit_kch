# ADR-015: 정책 축 분리
- 상태: 승인(2026-11-05)
- 관련: D-15
- 날짜: 2026-11-05

## 배경
v1에서는 restricted 정책(시험 제약)이 키트 전체의 전제였다.

## 선택지
1. `--policy standard|restricted`를 프로필과 별개의 축으로 둔다.
2. 프로필이 정책을 정한다(`hackathon` = restricted).

## 결정
**선택지 1.**
- 새 경로의 기본 정책은 `standard`다.
- 기존 경로는 `restricted`다.
- `hackathon` 프로필도 restricted를 강제하지 않는다.

## 근거
축을 분리해야 조합(policy × agent × profile)을 테스트할 수 있다.

## 결과와 위험
- 위험: 해커톤 사용자가 새 경로에서 `--policy`를 빠뜨릴 수 있다 → `hackathon` 프로필을 standard 정책으로 설치하면 보고서에 경고를 낸다.

## 되돌리는 방법
되돌릴 것이 없다(새 축을 추가할 뿐 기존 경로는 그대로다).
