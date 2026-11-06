# ADR-001: 공통 스킬의 원본 위치와 `.agents/skills` 처리
- 상태: 승인(2026-11-05)
- 관련: D-01, REQ-COMPAT-002, R-2, R-3
- 날짜: 2026-11-05

## 배경
키트 저장소 루트의 `.agents/skills/`에 기존 11개 스킬이 있다. 셸 전용 모드는 이 폴더의 **모든** 스킬을 복사한다(`bootstrap.sh:131`, `bootstrap.ps1:152-153`). 따라서 새 경로용 스킬을 이 폴더에 넣으면 restricted 셸 설치에 섞인다(R-3).

## 선택지
1. 원문 권장안: 모든 원본을 `shared/skills/`로 옮기고 `.agents/skills`는 생성 미러로 둔다. `devtools/sync_mirror.py --check`로 동기화를 강제한다. (장점: 원본이 한 곳이다. 단점: 11개를 옮기는 이동이 생기고, 미러 어긋남 위험(R-2)과 동기화 도구가 늘어난다.)
2. 현재 위치 유지: 기존 11개의 원본은 `.agents/skills/`에 그대로 둔다. `shared/skills/`에는 새 경로 전용 스킬, Q7 overlay, 키트가 작성한 새 스킬만 둔다. 외부 vendored 스킬은 `third_party/`(D-09)에 둔다. (장점: 이동도 미러 도구도 없다. 셸 모드, 테스트, 문서가 바뀌지 않는다. 단점: 원본 위치가 두 곳이 된다.)

## 결정
**선택지 2.** 원문 D-01이 허용한 대안이다("셸 모드, 테스트, 문서를 덜 바꾸면 그쪽을 택해도 된다").
- `.agents/skills/` = 기존 11개의 **원본이자** restricted 경로 설치 세트. 새 스킬을 넣지 않는다.
- `shared/skills/<name>/` = 키트가 작성한 새 경로용 스킬(`launch-compliance-check`, `add-skill-source`, `data-quality-validator` 등)
- `shared/skills/overlays/<name>/` = 기존 스킬의 standard 경로용 확장(Q7)
- `third_party/<owner>-<repo>/…` = 외부 vendored 스킬(D-09, D-21)
- 새 경로의 설치 목록은 카탈로그(`catalog/skills.json`)가 위 위치들에서 고른다.

## 근거
- 셸 모드 구조상 미러에 새 스킬이 들어가면 안 된다(01_ANALYSIS R-3, `bootstrap.sh:131`).
- 동기화 도구가 없으면 R-2 자체가 사라진다.
- 03_PLAN의 1차 의견("원본=미러 + 동기화 테스트")보다 단순하다. 그 의견은 이 ADR로 대체한다.

## 결과와 위험
- 테스트 V-22: `.agents/skills/`의 스킬 이름 집합이 기준선의 11개와 같고, 내용 해시도 기준선과 같다.
- 위험: 스킬 위치가 세 곳이라 처음 보는 사람이 헷갈릴 수 있다 → `shared/README.md`에 표로 설명한다.

## 되돌리는 방법
카탈로그가 위치를 추상화하므로, 나중에 원문 선택지 1로 옮길 때는 11개를 `shared/skills/`로 옮기고 미러 생성 스크립트만 추가하면 된다.
