# Codex 스킬 등록 및 로컬 병합

## 범위와 승인

사용자는 `add-skill-source`의 Codex 적용, 기존 NVIDIA 및 사용자 범위 설치 변경의 검증·커밋·로컬 병합, 병합된 로컬 브랜치 5개 정리를 승인했다. 추가로 두 클라이언트에 이식할 수 있는 전역 협업 설정과 이번 작업 브랜치의 GitHub 푸시·Draft PR을 승인했다. 원격 `main` 병합은 보류한다.

## 진행 상태

- 시작 커밋은 `e2d9039`다. `main`과 NVIDIA 브랜치의 커밋은 같았고 NVIDIA 변경은 작업 트리에만 있었다. Codex 작업은 별도 워크트리에 격리했다.
- Codex CLI 0.170.0의 로컬 `skills/list`가 `.codex/skills`와 `.agents/skills`의 양성 대조 스킬을 모두 `enabled`, `repo`로 반환했다. 저장소 전용 스킬은 `.codex/skills`에 둔다.
- 이전 브랜치는 로컬 `main` 도달 여부를 확인한 뒤 `git branch -d`로 정리한다. 사용자 전역 설정과 이미 배포된 커밋 이력은 보존한다.
- 계획과 검증 항목은 [TASK_BRIEF.md](TASK_BRIEF.md)에 기록한다.

## 검토

저장소 정책은 외부 검토 호출을 금지한다. 이 세션의 역할 선택기에 지정된 정확한 대체 모델 Codex 6 Terra가 없어 계획 단계 독립 교차 검토는 DEGRADED다.
