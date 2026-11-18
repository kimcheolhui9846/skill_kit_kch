# Codex · Claude Code 스킬 키트

Git과 Python 3.9 이상이 필요합니다. `python3`로 설치했다면 아래의 `python`을 `python3`로 바꾸세요.

## 1. 새 기기에서 한 번

작업할 프로젝트의 **부모 폴더**에서 실행합니다. 이미 그 위치에 `skill_kit_kch`의 `main`을 받아 두었다면 아래 `git clone` 대신 `git -C skill_kit_kch pull --ff-only`로 갱신하세요.

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

## 3. 프로젝트에서 MCP 사용하기

위의 기본 스킬 설치에는 MCP가 포함되지 않습니다. 아래에서 필요한 서버를 고르세요. 버전과 파일·네트워크 접근 범위는 [상세 카탈로그](docs/CATALOG.md)에 있습니다.

| MCP | 용도 | 등록 방법 |
|---|---|---|
| `sequential-thinking` | 문제를 단계별로 나누고 생각을 수정 | 키트 · `npx` |
| `playwright` | 브라우저 조작과 화면 테스트 | 키트 · `npx` |
| `context7` | 라이브러리 문서와 코드 예제 검색 | 키트 · `npx` |
| `inspo` | 디자인 레퍼런스와 디자인 시스템 검색 | 키트 · `npx` |
| `rea` | 프로젝트에서 Rea 에이전트 실행 | 키트 · `npx` |
| `codebase-memory` | 저장소 코드를 색인하고 탐색 | 키트 · `uvx` |
| `markitdown` | 파일이나 URL의 내용을 Markdown으로 변환 | 키트 · `uvx` |
| `mobbin` | 앱 화면과 사용자 흐름 검색 | 수동 가이드 · Claude Code |
| `nicelydone` | SaaS 화면과 사용자 흐름 검색 | 수동 가이드 · Claude Code |
| `refero` | 제품 화면과 사용자 흐름 검색 | 수동 가이드 · Claude Code |
| `ruflo` | 여러 에이전트의 작업 조율 | 수동 가이드 |
| `fetch` | URL 내용 가져오기 | 목록만 제공 |
| `git` | Git 저장소 조회와 조작 | 목록만 제공 |
| `filesystem` | 지정한 폴더의 파일 읽기·쓰기 | 목록만 제공 |
| `scrapling` | 웹 페이지에서 데이터 추출 | 목록만 제공 |
| `node_repl` | JavaScript 대화형 실행 | Codex 데스크톱 앱에서 관리 |

**키트로 설치하기.** 작업 프로젝트 루트에서 실행하세요. 아래 예시는 Codex와 Claude Code에 서버 3개를 함께 등록합니다. 원하는 서버마다 `--mcp 이름`을 넣고, 재설치할 때는 기존에 선택한 서버 중 계속 쓸 항목도 포함하세요. 표의 `npx` 항목은 Node.js가, `uvx` 항목은 uv가 필요합니다.

```bash
python ../skill_kit_kch/run_kit.py install --agent both --mcp sequential-thinking --mcp playwright --mcp context7
python ../skill_kit_kch/run_kit.py verify --agent both
```

같은 프로젝트에서 새 세션을 여세요. Codex는 프로젝트를 신뢰하면 `.codex/config.toml`을 읽고, Claude Code는 `.mcp.json`의 서버를 처음 사용할 때 승인을 요청합니다. 두 도구 모두 `/mcp`에서 연결 상태를 확인할 수 있습니다.

**수동 가이드 사용하기.** 아래 명령의 `mobbin`을 원하는 수동 항목 이름으로 바꾸면 등록 명령과 절차가 출력됩니다. 안내된 명령을 실행하고, Mobbin·Nicelydone·Refero는 Claude Code에서 `/mcp`를 열어 로그인하세요.

```bash
python ../skill_kit_kch/run_kit.py plan --agent claude --manual mobbin
```

[협업 설정 상세](user/workflow/README.md) · [설치 옵션과 제거](docs/guides/INSTALL.md) · [시험·오프라인·v1](docs/guides/EXAM_V1.md) · [개발](docs/guides/DEVELOPMENT.md)

시험 중에는 운영 환경에서 허용한 Codex만 사용하세요.
