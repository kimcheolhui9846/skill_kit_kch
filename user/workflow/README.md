# Codex·Claude Code 사용자 워크플로 설치

Python 3.9 이상으로 저장소 루트에서 다음 명령을 실행합니다. 추가 패키지와 네트워크 연결은 필요 없습니다.

```sh
python devtools/install_agent_workflow.py
python devtools/install_agent_workflow.py --apply
```

첫 명령은 파일마다 생성, 갱신, 변경 없음 여부를 표시합니다. `--apply`가 파일을 설치합니다.
설치가 끝나면 Codex와 Claude Code에서 새 세션을 시작하세요.

Codex에서 시작할 때는 `codex --model gpt-6.2-astra`로 계획 세션을 엽니다. Claude Code에서는 `/agents`로 `harness-opus-review`와 `harness-sonnet-worker`를 확인할 수 있습니다. 두 도구의 로그인과 해당 모델 사용 권한은 기기마다 필요합니다. 각 단계의 담당 모델과 인계 방법은 [공동 작업 지침](WORKFLOW.md)에 있습니다.

- Codex는 `CODEX_HOME` 또는 기본값 `~/.codex`를 사용합니다. 내용이 있는 `AGENTS.override.md`가 있으면 그 파일에, 그 외에는 `AGENTS.md`에 워크플로를 넣습니다. Codex 작업자 정의는 `agents/harness-sol-worker.toml`에 설치합니다.
- Claude Code는 `CLAUDE_CONFIG_DIR` 또는 기본값 `~/.claude`를 사용합니다. `CLAUDE.md`에 같은 워크플로를 넣고 `agents/`에 Opus 리뷰어와 Sonnet 작업자 정의를 설치합니다.

설치기는 사용자 지침 맨 위의 관리 구역을 갱신하며 주변 원문을 보존합니다. 같은 이름의 에이전트 파일에 설치기 소유권 표시가 없거나 관리 구역 표시가 잘못된 경우, 경로를 표시하고 파일을 쓰기 전에 중단합니다. 기존의 인증 및 클라이언트 설정 파일과 다른 에이전트 정의는 그대로 유지됩니다.

기존 파일을 바꿀 때는 옆에 `<파일명>.backup-<UTC 시각>-<고유값>`을 저장합니다. 복원하려면 원하는 백업 파일 내용을 원래 경로에 복사하세요. 설치가 중간에 멈추면 원인을 해결한 뒤 같은 `--apply` 명령을 다시 실행하면 됩니다. 파일별로 교체되므로 먼저 적용된 파일은 그대로 두고 남은 파일을 처리합니다. 강제 종료로 남은 `.workflow-stage-*` 임시 파일은 클라이언트가 읽지 않습니다.
