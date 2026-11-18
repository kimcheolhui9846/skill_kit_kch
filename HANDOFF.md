# Codex 스킬 등록 및 로컬 병합

## 범위와 승인

사용자는 `add-skill-source`의 Codex 적용, 기존 NVIDIA 및 사용자 범위 설치 변경의 검증·커밋·로컬 병합, 병합된 로컬 브랜치 5개 정리를 승인했다. 추가로 두 클라이언트에 이식할 수 있는 전역 협업 설정과 이번 작업 브랜치의 GitHub 푸시·Draft PR을 승인했다. 원격 `main` 병합은 보류한다.

## 진행 상태

- 시작 커밋은 `e2d9039`다. `main`과 NVIDIA 브랜치의 커밋은 같았고 NVIDIA 변경은 작업 트리에만 있었다. Codex 작업은 별도 워크트리에 격리했다.
- Codex CLI 0.170.0의 로컬 `skills/list`가 `.codex/skills`와 `.agents/skills`의 양성 대조 스킬을 모두 `enabled`, `repo`로 반환했다. 저장소 전용 스킬은 `.codex/skills`에 둔다.
- 로컬 `main`에 작업 브랜치를 fast-forward로 병합했다. `merge-base --is-ancestor`로 확인한 이전 브랜치 `docs/packs-and-mcp`, `docs/powershell-note`, `docs/readme-v2`, `feat/v2-multi-agent`, `fix/one-line-install`은 `git branch -d`로 정리했다.
- 원격에는 `codex/task-add-skill-source` 브랜치를 게시했다. [Draft PR #15](https://github.com/kimcheolhui9846/skill_kit_kch/pull/15)의 대상은 `main`이다. [작업 범위와 검증 계획](TASK_BRIEF.md).

## 검토

저장소의 외부 전송 제한에 따라 Opus의 계획·마일스톤 교차 검토는 수행하지 않았다. 실제 서비스 계정을 통한 모델 간 전체 인계는 미검증이다. 주 세션이 코드, 검증 결과, 설정, 브랜치와 PR 상태를 직접 확인했다. 최종 판정은 `PASS WITH NOTES`다.

## 구현 및 검증

- `--skills-only` 재설치에서 이전의 전체 설치 항목을 삭제 대상으로 잡는 문제를 재현했다. 프로필 밖 소유 기록을 보존했고 새 형식과 이전 매니페스트의 전환을 검증했다. 사용자 범위·정리 테스트는 74개 통과, 1개 건너뜀이었다.
- 이식용 설치기는 승인된 텍스트와 역할 파일 5개를 관리한다. 임시 홈 테스트 10개가 통과했고, 실제 홈에서 적용 후 재실행한 미리보기의 5개 항목이 모두 `UNCHANGED`였다. 기존 Codex TOML과 Claude 설정 JSON 해시는 일치했다.
- Claude Code 2.1.327은 로컬 초기화 요청에서 두 사용자 역할과 모델 배정을 반환했다. 실제 모델 추론 호출은 수행하지 않았다.
- 첫 전체 테스트 중 손상된 프로필을 다루는 테스트가 로컬 `.kit` 임시 폴더까지 복사하다가 Windows 경로 오류로 실패했다. 복사 대상에서 이 폴더를 제외했다.
- 고정 출처 28개는 오프라인 해시 일치. 저장소 가이드와 테스트가 현재 기본 스킬 18개를 기준으로 사용한다.
- 메인 README는 Git 기준 36줄이다. 새 기기의 전역 설정과 선택적 프로젝트 설치를 남겼다. 문서 명령 실행기에서 95개 명령이 예상 종료 코드를 반환했다.
- 최종 pytest는 문서 명령 파일 88개 통과, 나머지 1,941개 통과·2개 건너뜀으로 총 2,029개 통과, 실패 0개다. `ruff check .`, `ruff format --check .`, `git diff --check`가 통과했다.
- 병합한 실제 저장소에서 Codex가 `add-skill-source`를 `scope=repo`, `enabled=true`로 반환했다. 다른 기기에서는 PR의 브랜치를 받은 뒤 README에 따라 설치한다.
