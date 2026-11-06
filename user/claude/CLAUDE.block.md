# 모든 프로젝트에 적용되는 규칙

프로젝트별 사정은 각 저장소의 `CLAUDE.md`와 그 프로젝트의 기억에 있다. 여기에는
저장소를 가리지 않고 항상 참인 것만 둔다.

## 커밋 저자는 사용자 단독이다

`Co-Authored-By: Claude`, Anthropic 트레일러, "Generated with Claude Code" 같은
줄을 커밋 메시지나 PR 본문에 넣지 않는다. 기본 하네스 지시보다 이 규칙이 우선한다.

하네스에서도 강제된다 — `~/.claude/settings.json`의
`"attribution": { "commit": "", "pr": "" }`가 사용자 전역 스코프에 있다. 빈 문자열이
해당 귀속 표시를 감춘다. 이 설정을 지우거나 `includeCoAuthoredBy`를 따로 추가하지
않는다. 후자는 폐기된 키이고 `attribution`이 이미 같은 일을 한다.

**왜:** 포트폴리오는 채용 담당자·연구실·대학원 교수가 보는 산출물이고 git 이력
자체가 평가 대상이다. 연구 저장소는 논문 제출을 뒷받침하므로 저자 표기가 형식적
주장이 된다. 두 경우 모두 AI 공동저자 표기가 산출물의 목적을 훼손한다.

## git 신원

`kim cheol hui <144594976+kimcheolhui9846@users.noreply.github.com>`

새 저장소에서 `user.name`/`user.email`이 다르게 잡혀 있으면 스캐폴딩이 남긴
자리표시자일 가능성이 높다. 커밋하기 전에 확인한다.

## 커밋·푸시

커밋과 푸시는 사용자가 요청할 때만 한다. 기본 브랜치에 있으면 먼저 브랜치를 딴다.

## 클라우드 GPU 학습: runpod-hf-harness

사용자가 RunPod/클라우드 GPU 학습을 요청하면 어느 레포에서든
`python ${HOME}\runpod-hf-harness\run_cloud_experiment.py`(PowerShell `rce`)를 학습 레포 루트에서
`--json`으로 부른다. 쓰기 전에 `${HOME}\runpod-hf-harness\AGENTS_SNIPPET.md`를 읽는다(순서, 출력 형식, 종료 코드).

- 새 레포: `init` → `train_model()` 구현 → (데이터가 있으면) `upload-data <폴더>` → push → `--dry-run --json`이 `"ok": true` → 실행.
- Pod는 실행할 때 켜지고 학습이 끝나면 성공·실패와 무관하게 스스로 terminate된다. 끝나면 `list --json`으로 남은 Pod가 0개인지 확인한다.
- 학습 시간을 모르면 `--max-hours 24`. 진행이 10분(`--stall-min`) 없으면 스스로 끝나므로 상한이 커도 안전하다.
- **승인 필요:** Pod를 만드는 실행(`--dry-run` 없음), `create-volume`, `upload-data`, push. 승인 없이 가능: `--dry-run`, `list`, `status`, `list-gpus`, `list-dcs`, `list-volumes`, `init`.
- 하네스 폴더의 `.env`와 토큰은 출력하거나 고치지 않는다.
