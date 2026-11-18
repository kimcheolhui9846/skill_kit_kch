# Codex · Claude Code 스킬 키트

Git과 Python 3.9 이상이 필요합니다. `python3`로 설치했다면 아래의 `python`을 `python3`로 바꾸세요.

## 1. 새 기기에서 한 번

작업할 프로젝트의 **부모 폴더**에서 실행합니다. 키트는 프로젝트 옆 `skill_kit_kch` 폴더에 받습니다. 이미 그 위치에 받았다면 `git clone`만 건너뛰세요.

```bash
git clone https://github.com/kimcheolhui9846/skill_kit_kch.git
```

같은 부모 폴더에서 이어서 실행합니다.

```bash
cd skill_kit_kch
python devtools/install_agent_workflow.py
python devtools/install_agent_workflow.py --apply
```

첫 Python 명령으로 변경할 전역 파일을 확인한 뒤 `--apply`로 협업 설정을 적용합니다. Codex와 Claude Code에 로그인하고 새 세션을 여세요.

## 2. 프로젝트에 스킬이 필요할 때만

키트와 나란히 있는 **작업 프로젝트 루트**에서 실행합니다.

```bash
python ../skill_kit_kch/run_kit.py install --agent both
python ../skill_kit_kch/run_kit.py verify --agent both
```

`Status: READY`를 확인하고 같은 프로젝트에서 에이전트를 다시 열어 `/skills`를 확인하세요.

[협업 설정 상세](user/workflow/README.md) · [설치 옵션과 제거](docs/guides/INSTALL.md) · [시험·오프라인·v1](docs/guides/EXAM_V1.md) · [개발](docs/guides/DEVELOPMENT.md)

시험 중에는 운영 환경에서 허용한 Codex만 사용하세요.
