# hackathon-agent-kit

> **Claude Code 사전 개발 전용 / 시험 중 사용 불가.** 이 저장소는 시험 전에 Claude Code로 개발했다. 시험 중에는 운영 환경이 제공하는 에이전트만 사용한다. 키트는 에이전트가 읽을 정책 파일과 Skill 파일을 작업 공간에 배치할 뿐이며, 외부 모델을 호출하지 않는다. `--offline`이면 네트워크도 쓰지 않는다.

작업 공간에 **Codex**와 **Claude Code**용 정책 파일, Skill, MCP 설정을 안전하게 설치한다. 결과는 READY / PARTIAL / BLOCKED로 보고한다. 사람이 Task마다 승인하는 작업 흐름(HITL)도 함께 제공한다.

- **두 에이전트:** `--agent codex`, `--agent claude`, `--agent both`.
- **수명 주기:** 미리 보기(`plan`), 설치, 검증, 업데이트, 제거, 백업 복원, 진단.
- **고르는 설치:** 프로필 8개와 팩 9개를 조합한다. 외부 스킬 팩은 고를 때만 설치된다.
- **안전 장치:**
  - 사용자 파일은 덮어쓰지 않고, 대상 밖에는 쓰지 않는다.
  - MCP 설정 감사를 쓰기 **전에** 한다. 막히면 아무것도 쓰지 않는다.
  - MCP·플러그인은 카탈로그의 고정 버전만 쓰고, 기본은 꺼져 있다.
  - 네트워크는 확인을 받은 뒤에만 쓴다.
- **HITL:** Task 상태 기계와 승인 기록, 요구사항 추적, JUnit 기반 테스트 보고, 반례 기록, 세션 복구.
- **기존 사용법 유지:** 명령 없이 부르는 v1 사용법(`bootstrap.sh`, `bootstrap.ps1 --profile python` 등)은 v1과 똑같이 동작한다. 시험 당일 안내는 아래 "기존 사용자 안내"에 있다.

## 빠른 시작

**작업 폴더 안의 터미널에서** 아래 한 줄을 실행한다. 이 명령 하나가 다음을 모두 한다.

1. 키트를 작업 폴더 **밖**(형제 폴더 `../skill_kit_kch`)에 받는다. 이미 받아 두었으면 최신으로 갱신한다.
2. Codex와 Claude Code 양쪽에 설치한다.

키트를 밖에 두는 것은 키트 폴더가 제출물에 섞이지 않게 하려는 것이다. 그래서 작업 폴더 안에 bootstrap 파일이 없는 것은 정상이다.

Windows PowerShell:

```powershell
$k='..\skill_kit_kch'; if (Test-Path "$k\.git") { git -C $k pull --ff-only } elseif (Test-Path $k) { Write-Error "$k 폴더가 있지만 git 저장소가 아닙니다. 지우거나 옮긴 뒤 다시 실행하세요." } else { git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git $k }; if ($? -and $LASTEXITCODE -eq 0) { powershell -NoProfile -ExecutionPolicy Bypass -File "$k\bootstrap.ps1" install --agent both }
```

bash (Linux, macOS, Git Bash, WSL):

> Windows에서는 위의 PowerShell 줄을 쓴다. PowerShell 창에 아래 bash 줄을 넣거나 `bash ...`를 실행하면 WSL의 bash가 떠서 경로가 어긋난다. 그러면 `No such file or directory`가 나온다.

```bash
k=../skill_kit_kch; if [ -d "$k/.git" ]; then git -C "$k" pull --ff-only; elif [ -e "$k" ]; then echo "$k 폴더가 있지만 git 저장소가 아닙니다. 지우거나 옮긴 뒤 다시 실행하세요." >&2; false; else git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git "$k"; fi && bash "$k/bootstrap.sh" install --agent both
```

- 끝의 `--agent both`를 `--agent codex`나 `--agent claude`로 바꾸면 한쪽에만 설치한다. 같은 줄을 다시 실행하면 키트를 갱신하고 다시 적용한다.
- 끝에 `Status:       READY`가 나오면 끝난 것이다.
- **에이전트에게 실행을 맡길 때:** 에이전트 샌드박스는 보통 네트워크가 막혀 있다. 그러면 clone이 실패해서 "bootstrap 파일이 없다"는 말이 나온다. 터미널에서 직접 실행하거나, 에이전트에게 네트워크 사용을 허락한다.
- 이 두 줄은 네트워크가 필요해서 자동 문서 명령 기록에는 들어 있지 않다(미검증 목록). 대신 2026-11-09에 Windows PowerShell 5.1과 Git Bash에서 세 경우를 직접 실행했다.
  - 빈 작업 폴더: 받고 설치해서 `READY`.
  - 두 번째 실행: `Already up to date` 뒤 다시 `READY`.
  - git이 아닌 `../skill_kit_kch` 폴더가 있을 때: 안내 문구를 내고 설치하지 않음.

이미 받아 둔 키트로 다시 설치하거나 한쪽만 설치하려면 아래 명령을 쓴다.

### Codex

```bash
bash ../skill_kit_kch/bootstrap.sh install --agent codex
```

### Claude Code

```bash
bash ../skill_kit_kch/bootstrap.sh install --agent claude
```

### 둘 다

```bash
bash ../skill_kit_kch/bootstrap.sh install --agent both
```

Windows PowerShell에서는 같은 인수를 `bootstrap.ps1`에 준다.

```powershell
..\skill_kit_kch\bootstrap.ps1 install --agent both
```

- `.ps1`이 실행 정책으로 막히면 그 프로세스에만 허용한다: `powershell -ExecutionPolicy Bypass -File ..\skill_kit_kch\bootstrap.ps1 install --agent both`.
- Python이 있으면 `python ../skill_kit_kch/run_kit.py install --agent both`도 같다.

**설치 뒤 확인:**
1. 출력 끝의 `Status:`가 `READY`인지 본다. 예시: `docs/examples/v2-install-both.log`.
2. 에이전트를 **설치한 작업 폴더에서** 새로 연다.
3. Codex와 Claude Code 모두 `/skills`로 키트 Skill이 보이는지 확인한다.
4. 보고서의 `Load UNVERIFIED`는 정상이다. 에이전트가 실제로 읽었는지는 에이전트 안에서만 볼 수 있다. 검토자 점검표는 `docs/v2/AGENT_LOAD_CHECK.md`다.

## 설치되는 것 (기본: 프로필 `core,hitl`, 정책 `standard`)

| | Codex | Claude Code |
|---|---|---|
| 정책 | `AGENTS.md`의 키트 구간 | `CLAUDE.md`의 키트 구간 |
| Skill(17개) | `.agents/skills/` | `.claude/skills/` |
| MCP(프로필이나 `--mcp`로 고른 것만) | `.codex/config.toml`의 키트 구간 | `.mcp.json`의 키트 소유 키 |
| 기타 | 승인 훅(`--hooks`) | 승인 훅(`--hooks`), 반례용 서브에이전트, 플러그인 선언(`--plugin`) |

- `--policy restricted`는 v1과 같은 Skill 11개만 설치한다(시험용). 외부 스킬 팩은 restricted에서 설치되지 않는다.
- 상태와 백업은 대상의 `.kit/`에 남는다. 제거(`uninstall`)는 키트가 쓴 것 중 내용이 그대로인 것만 지운다.

## 프로필과 팩

`--profile`에 쉼표로 여러 개를 준다. 예: `--profile core,motion`은 기본 Skill 17개에 motion 팩 16개를 더해 33개를 설치한다. 설치 전에 `kit profiles show core,motion`으로 실제로 들어갈 Skill을 볼 수 있다.

| 종류 | 이름 | 내용 |
|---|---|---|
| 프로필 | `core` | 정책과 키트 Skill. 도구와 MCP 없음 |
| 프로필 | `python`, `data`, `web`, `full` | v1 프로필. 도구 확인과 `sequential-thinking` MCP |
| 프로필 | `hackathon`, `fullstack`, `ai-research` | 시간 제한 대회, 프런트·백엔드, 실험·연구용 조합 |
| 팩 | `hitl`, `workflow`, `research`, `launch` | 승인 흐름, 계획 체인(superpowers), 실험·통계, 출시 전 점검 |
| opt-in 팩 | `eng-patterns`, `lean`, `cloudflare`, `motion`, `planning-extras` | 외부 스킬 44개. standard 정책에서 고를 때만 설치된다 |

- 외부 스킬은 커밋을 고정해 `third_party/`에 그대로 복사했고, 라이선스는 `THIRD_PARTY_NOTICES.md`에 있다.
- 전역 설치나 토큰 저장을 지시하는 스킬 등 위험한 것은 팩에서 뺐다. 이유는 팩 설명(`kit profiles list`)과 `docs/v2/07_SOURCES_EVALUATION.md`에 있다.
- 프로필별 Skill 전체 목록은 `docs/CATALOG.md`에 있다.

## MCP, 플러그인, 수동 도구

| 종류 | 고르는 법 | 키트가 하는 일 |
|---|---|---|
| MCP 서버(stdio) | 프로필 또는 `--mcp <이름>` | 고정 버전의 `npx`/`uvx` 명령을 작업 공간 설정에 쓴다. 위험도가 높거나 키가 필요한 서버는 기본으로 꺼져 있다 |
| Claude 플러그인 | `--plugin <이름>` | 고정 커밋의 설치 명령을 선언·출력한다 |
| 수동 도구 | `--manual <이름>` | 설치 단계, 위험, 되돌리는 법을 출력만 한다. 실행하지 않는다 |
| 원격 MCP | 수동 안내만 | 카탈로그에 등록하지 않는다. 연결 명령은 사용자가 직접 실행한다 |

- API 키 값은 설정 파일에 쓰지 않고 환경 변수 이름만 참조한다.
- 전체 목록, 위험도, 고정 버전은 `docs/CATALOG.md`와 `sources.lock.json`에 있다.

## 외부 스킬 추가

GitHub 주소에서 Skill을 받아 키트에 더한다. 먼저 계획만 보여 주고, `--yes`를 줘야 쓴다.

| 단계 | 명령 |
|---|---|
| 계획 보기 | `kit source add <owner/repo> [--path P]... [--pack K]` |
| 반영 | 같은 명령에 `--yes` |
| 확인 | `kit source check`, `kit source list` |

- 고정 커밋으로 메모리에서 받고, 라이선스, 비밀값, 형식을 검사한다. 저장소의 코드는 실행하지 않는다.
- 새 출처는 standard 정책에만 쓰인다. 자세한 절차는 `docs/v2/adr/ADR-021-source-add-pipeline.md`에 있다.

## 자주 쓰는 명령

아래 `kit`은 `bootstrap.sh`, `bootstrap.ps1`, `python run_kit.py` 중 하나다.

| 하려는 일 | 명령 |
|---|---|
| 쓰기 전에 미리 보기 | `kit plan --agent both` |
| 설치 | `kit install --agent both` |
| 네트워크 없이 | `kit install --agent both --offline` |
| 팩을 더해 설치 | `kit install --agent both --profile core,motion` |
| 프로필·팩 보기 | `kit profiles list`, `kit profiles show <이름> --policy standard` |
| 검증 | `kit verify --agent both` |
| 키트 업데이트 뒤 다시 맞추기 | `kit update --agent both` |
| 제거 | `kit uninstall --agent both` |
| 백업에서 되돌리기 | `kit restore --backup <시각>` |
| 진단 | `kit doctor` |
| Task 승인 흐름 | `kit task …`, `kit req …`, `kit recover` |
| 도움말 | `kit help` (v1 도움말은 `kit --help`) |

종료 코드: 0 READY, 1 PARTIAL, 2 BLOCKED, 64 잘못된 인수, 65 대상 문제.

## 문서

| 문서 | 내용 |
|---|---|
| `docs/guides/INSTALL.md` | 설치·미리 보기·검증·업데이트·제거·복구·오프라인, Windows/Linux |
| `docs/guides/CODEX.md` | Codex 전용: 신뢰 설정, 로드 확인, 제약 |
| `docs/guides/CLAUDE_CODE.md` | Claude Code 전용: 프로젝트/사용자 설정, 플러그인, 훅 |
| `docs/guides/HITL_WORKFLOW.md` | Task 승인, 테스트 보고, 추적, 반례, 세션 복구 |
| `docs/guides/MIGRATION_V1_TO_V2.md` | v1과의 호환, 달라진 점, 옮기는 절차, 되돌리기 |
| `docs/CATALOG.md` | Skill, 팩, MCP, 플러그인, 수동 도구 목록(생성 문서) |
| `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/COMPATIBILITY.md` | 구조, 보안과 네트워크, 지원 환경 |
| `docs/TEST_REPORT.md`, `docs/v2/FINAL_REPORT.md` | 테스트 결과와 최종 검증 보고서 |
| `docs/examples/` | 실제 실행 로그(v1: `install.log` 등, v2: `v2-*.log`) |
| `docs/v2/` | v2 설계, ADR, 출처 평가, 회귀 기록, 검토자 점검표 |

# 기존 사용자 안내 (v1 사용법)

명령 없이 부르는 사용법은 v1과 똑같이 동작한다(Codex 전용, Skill 11개). 아래는 v1 README의 안내를 그대로 옮긴 것이다. 시험 당일 절차도 여기에 있다. v2로 옮기려면 `docs/guides/MIGRATION_V1_TO_V2.md`를 본다.

### 한 줄 설치

저장소 주소는 `https://github.com/kimcheolhui9846/skill_kit_kch`다. 설치는 기본 브랜치 `main`에서 받으므로, 시험 전에 작업 브랜치를 `main`에 병합해 둔다. 복제와 실행은 분리돼 있다(`curl | bash` 방식 아님). 키트는 작업 공간 **밖**(형제 폴더 `../skill_kit_kch`)에 복제한다. 그래야 키트 폴더가 제출물에 섞이지 않는다. 아래 명령은 작업 공간 안에서 실행한다.

bash (Linux/macOS/Git Bash):

```bash
git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git ../skill_kit_kch && bash ../skill_kit_kch/bootstrap.sh --target .
```

Windows PowerShell:

```powershell
git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git ..\skill_kit_kch; if ($LASTEXITCODE -eq 0) { & ..\skill_kit_kch\bootstrap.ps1 --target . }
```

실행 정책 때문에 `.ps1`이 막히면 스크립트를 우회하지 말고 아래 "스크립트를 실행할 수 없을 때"를 따른다.

### 시험 당일 설치: 두 가지 방법

코파 원격 환경 시험에서는 **방법 1**을 쓴다. 명령은 미리 복사해 두거나 메모에 띄워 둔다. 원격 환경에서 GitHub 접속, Python, Node가 되는지는 사전 체험 때 `docs/RULES_CHECKLIST.md`로 확인한다.

#### 코파 환경에서는 Codex에게 설치를 시킨다

2026-10-30 사전 체험에서 확인했다. 플랫폼 터미널에서 직접 실행하면 설치가 되지 않았고, **Codex에게 명령을 실행해 달라고 하면** Skill이 설치됐다.

1. 코파 환경에서 Codex를 연다.
2. "아래 명령을 실행해 줘"라고 하고 방법 1의 PowerShell 명령을 붙여 넣는다.
3. 출력 끝의 `Status:` 줄이 `READY`인지 확인한다.
4. **Codex 세션을 새로 시작한다.** 켜져 있던 세션은 새로 설치한 Skill과 MCP를 읽지 못할 수 있다.
5. 아래 "설치 뒤 공통 확인"을 따른다.

#### 방법 1. 공개 저장소에서 받아 설치 (어느 PC든)

작업 폴더 안에서 실행한다. 키트는 형제 폴더 `..\skill_kit_kch`에 받는다.

```powershell
$k='..\skill_kit_kch'; if (Test-Path "$k\.git") { git -C $k pull --ff-only } elseif (Test-Path $k) { Write-Error "$k 폴더가 있지만 git 저장소가 아닙니다. 지우거나 옮긴 뒤 다시 실행하세요." } else { git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git $k }; if ($? -and $LASTEXITCODE -eq 0) { & "$k\bootstrap.ps1" }
```

```bash
k=../skill_kit_kch; if [ -d "$k/.git" ]; then git -C "$k" pull --ff-only; elif [ -e "$k" ]; then echo "$k 폴더가 있지만 git 저장소가 아닙니다." >&2; false; else git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch.git "$k"; fi && bash "$k/bootstrap.sh"
```

이미 받아 둔 키트가 있으면 clone 대신 갱신한다. 그래서 두 번 실행해도 "already exists"로 멈추지 않는다.

`--target`을 빼면 현재 폴더에 설치한다. 프로필은 끝에 `--profile python`처럼 붙인다. 이 방법은 당일 GitHub에 접속할 수 있어야 한다.

#### 방법 2. 개인 노트북에 미리 세팅하고 함수로 호출

**코파 플랫폼 시험에는 쓸 수 없다.** 시험은 코파가 제공하는 원격 환경의 Codex에서 진행되므로 노트북 설정이 넘어가지 않는다. 시험 당일에는 방법 1을 쓴다. 이 방법은 본인 PC에서 연습하거나, Codex를 로컬에서 직접 쓰는 경우를 위한 것이다.

시험 전에 노트북에서 한 번만 한다.

1. git, Python 3.9 이상, Codex를 설치한다. MCP를 쓰려면 Node.js도 설치한다.
2. 키트를 고정 위치에 받는다.
   ```powershell
   git clone https://github.com/kimcheolhui9846/skill_kit_kch C:\kit
   ```
3. 스크립트 실행을 현재 사용자에게만 허용한다(관리자 권한 불필요).
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
4. PowerShell 프로필에 함수를 등록한다. `notepad $PROFILE`로 열고(파일이 없으면 먼저 `New-Item -ItemType File -Force $PROFILE`) 아래를 붙여 넣는다.
   ```powershell
   function kit { & "C:\kit\bootstrap.ps1" @args }
   function kit-update { git -C C:\kit pull --ff-only }
   ```
5. PowerShell을 새로 열고 빈 폴더에서 `kit`을 실행해 `Status: READY`가 나오는지 확인한다.

당일에는 작업 폴더에서 `kit` 또는 `kit --profile python`만 친다. 설치에 네트워크가 필요 없다. 시험 전날 `kit-update`로 최신 버전을 받아 둔다.

#### 설치 뒤 공통 확인

1. Codex를 **키트를 설치한 작업 폴더에서** 연다. 다른 폴더에서 열면 키트 Skill이 보이지 않는다.
2. 신뢰(trust) 확인창이 뜨면 신뢰를 고른다. MCP는 신뢰한 폴더에서만 켜진다. Skill과 AGENTS.md는 신뢰와 무관하게 읽힌다.
3. `/skills`로 키트 Skill을, `/mcp`로 `sequential-thinking`을 확인한다. 안 보이면 `docs/RULES_CHECKLIST.md`의 대체 경로를 따른다.
4. MCP가 안 보여도 시험은 진행할 수 있다. 핵심은 Skill과 AGENTS.md다. 신뢰, 재시작, `node --version` 순으로 한 번 확인하고 안 되면 MCP 없이 간다.

### 프로필

| 프로필 | 내용 |
|---|---|
| `core` | AGENTS.md and the eleven kit skills. Installs no tools and no MCP servers. (기본값) |
| `python` | core plus pytest and ruff (installed only when missing) and the sequential-thinking MCP server. |
| `data` | python plus a check for numpy and pandas. Never installs them; prints the install command instead. |
| `web` | core plus a read-only check of the target's package.json, lockfile and engines.node, and the sequential-thinking MCP server. Installs nothing. |
| `full` | Development only. Checks every candidate (python, data, web, MCP) and reports what it would install; installs no tools. |

### 옵션

| 옵션 | 의미 |
|---|---|
| `--profile <이름>` | `core`(기본), `python`, `data`, `web`, `full` |
| `--target <dir>` | 설치 대상 작업 공간(기본: 현재 디렉터리) |
| `--dry-run` | 아무것도 쓰지 않고 계획만 출력. 설치하지 않고 서버를 시작하지 않는다(`--version` 점검은 실행한다) |
| `--verify-only` | 설치·등록 없이 현재 상태만 검사(로그만 기록). `--offline`이나 `--no-mcp`가 아니면 MCP 핸드셰이크(`npx -y`, 네트워크와 대상 밖의 npm 캐시 사용)는 여전히 실행한다 |
| `--offline` | 네트워크를 쓰지 않음. 도구 설치와 MCP 핸드셰이크를 건너뜀(`SKIPPED`) |
| `--no-mcp` | `.codex/config.toml` 블록을 만들지 않고 MCP 항목을 건너뜀 |
| `--verbose` | 파일·항목별 상세 출력 |
| `--help` | 도움말 |

네트워크는 `python` 프로필이 pytest·ruff를 설치할 때(`uv tool install`, 실패하면 `pip install --user`)와 MCP 핸드셰이크(`npx -y`)에서만 쓴다. `core`와 `web`은 도구를 설치하지 않는다. 쓰는 경우 보고서의 `Network:` 줄에 표시한다. 자세한 내용은 `docs/SECURITY.md`를 본다.

### MCP

`python`, `data`, `web`, `full` 프로필(`data`와 `full`은 `python`을 상속한다)은 대상의 `.codex/config.toml`에 `sequential-thinking` 서버 하나를 등록한다(`npx -y @modelcontextprotocol/server-sequential-thinking@2026.8.31`, stdio). `fetch`, `git`, `filesystem`은 후보로 기록만 하고 등록하지 않는다(사유는 `docs/SECURITY.md`). 같은 프로필들이 `npx -y` 핸드셰이크도 한다. `full`은 도구 설치만 건너뛴다. 등록은 `# hackathon-kit:begin` … `# hackathon-kit:end` 구간 안에서만 이루어지며 전역 설정은 건드리지 않는다.

Codex는 `.codex/config.toml`을 신뢰된 프로젝트에서만 로드한다. 프로젝트를 신뢰하기 전에는 `codex-mcp` 항목이 `UNVERIFIED`로 나오며 정상이다. 신뢰한 뒤 Codex에서 `/mcp`로 확인한다. MCP가 필요 없으면 `--no-mcp`를 쓴다.

이전 실행에서 쓴 키트 구간이 `.codex/config.toml`에 남아 있는데 이번에는 MCP를 쓰지 않는 경우(`--no-mcp`, `core` 프로필) 키트는 아무것도 지우지 않고 선택 항목 `mcp-config`를 `FAIL`(상태 `PARTIAL`)로 보고하며 `MCP:` 줄에 `earlier kit block still registered`를 덧붙인다. 원하지 않으면 `.codex/config.toml`에서 `# hackathon-kit:begin`부터 `# hackathon-kit:end`까지 직접 지운다.

Python 3.9~3.10(`tomllib` 없음)이나 TOML이 깨진 경우에도 감사는 줄 단위 검사로 원격 서버, 금지 키, 비밀 이름 env를 찾아 FAIL로 보고한다. 아무것도 못 찾으면 `UNVERIFIED`이며 `Items:`와 `Next action:`에 표시된다. 전체 감사는 Python 3.11+에서 한다.

### 종료 코드

| 코드 | 상태 | 의미 |
|---|---|---|
| 0 | READY | 필수 항목 모두 검증(또는 dry-run 완료) |
| 1 | PARTIAL | 필수 항목은 정상, 선택 항목 일부 실패 또는 Python 없이 셸 모드로 실행 |
| 2 | BLOCKED | 필수 항목 실패 또는 사용자 판단이 필요한 충돌. 셸 모드에서 파일 쓰기에 실패한 경우도 포함 |
| 64 | - | 잘못된 인수 |
| 65 | - | 대상 디렉터리가 없거나 디렉터리가 아님 |

### 예상 출력

```text
Environment:  Windows 11 AMD64, shell=powershell, python 3.12.10
Tools:        git OK, uv OK, node OK, npx OK, codex OK, python OK
Target:       D:\work\task
Profile:      core
AGENTS.md:    INSTALLED
Skills:       11 expected / 11 verified
Codex load:   UNVERIFIED (open Codex and run /skills)
MCP:          none in profile 'core'
Network:      not used
Status:       READY
Next action:
  - Open Codex in D:\work\task and run /skills to confirm the kit skills load.
```

예시 로그는 `docs/examples/`(설치, 재실행, 실패, 오프라인, 충돌)에 있고 `uv run python devtools/make_examples.py`로 다시 만든다(네트워크 사용 없음).

`Codex load: UNVERIFIED`는 정상이다. Codex가 Skill을 실제로 읽었는지는 Codex 안에서 `/skills`로만 확인할 수 있다.

### 안전 장치

- 기존 `AGENTS.md`는 덮어쓰지 않는다. 키트 내용은 `<!-- hackathon-kit:begin -->` … `<!-- hackathon-kit:end -->` 구간에만 쓰고, 수정 전 원본을 `.kit/backups/<시각>/`에 남긴다.
- 키트 구간 안의 줄바꿈이 CRLF여도 비교 전에 정규화한다. 편집기나 git `autocrlf`가 줄바꿈을 바꿔도 충돌로 보지 않는다.
- 사용자가 고친 파일은 `CONFLICT`로 보고하고 건드리지 않는다. `AGENTS.md`가 디렉터리이거나 읽을 수 없는 파일인 경우도 `CONFLICT`로 보고한다.
- 같은 명령을 다시 실행해도 결과가 같다(멱등). 중간에 실패해도 다시 실행하면 이어서 맞춰진다.
- 대상 디렉터리 밖에는 쓰지 않으며 `~/.codex` 같은 전역 설정은 건드리지 않는다.
- 로그는 대상의 `.kit/logs/`에만 남고 토큰 형태 문자열은 가려진다. `GITHUB_TOKEN=`, `OPENAI_API_KEY=`처럼 접두어가 붙은 이름과 `Bearer` 값도 가린다.
- Python이 없을 때의 셸 전용 모드는 파일을 `.kit-tmp` 임시 파일에 쓴 뒤 제자리로 옮긴다. 쓰기에 실패하면 `Status: BLOCKED`(종료 코드 2)로 끝난다.

### 키트 폴더 위치

- 대상(`--target`, 기본은 현재 디렉터리)이 키트 폴더 자신이면 종료 코드 65로 거부한다(키트의 `AGENTS.md`가 원본이자 대상이 되어 망가지는 것을 막는다). 작업 공간에서 실행하거나 `--target <작업 공간>`을 준다. 빈 문자열 `--target ""`은 종료 코드 64다.
- 키트는 작업 공간 밖의 형제 폴더에 복제하는 것을 권장한다. 작업 공간 안에 복제했다면 설치 후 키트 폴더를 삭제해 제출물에 남지 않게 한다.

### 셸 전용 모드의 한계

Python 3.9+가 없으면 `bootstrap.sh`/`bootstrap.ps1`이 `AGENTS.md`와 Skill만 복사한다(종료 코드 1, `Status: PARTIAL`). 어떤 프로필을 골라도 마찬가지이며 도구 설치와 MCP는 없다. 제한 사항:

- `--verify-only`는 거부한다(종료 코드 64, 아무것도 쓰지 않음). 검증은 Python이 필요하다.
- `--offline`, `--no-mcp`, `--verbose`는 아무 효과가 없다.
- 백업, 로그(`.kit/`), 기존 `AGENTS.md`와의 병합은 Python 모드에서만 된다. 기존 `AGENTS.md`에 키트 구간이 없으면 `CONFLICT`로 두고 직접 추가하라고 안내한다.
- 이미 있는 Skill 폴더는 내용을 검사하지 않고 건너뛴다(`exists, not checked`).

### 스크립트를 실행할 수 없을 때

키트 폴더의 `AGENTS.md` 내용과 `.agents/` 폴더를 작업 공간 루트에 그대로 복사하면 된다. 그다음 Codex에서 `/skills`로 확인한다.

### v1 문서

- `docs/RULES_CHECKLIST.md`: 사전 체험 체크리스트와 규칙
- `docs/TROUBLESHOOTING.md`: 메시지별 대응
- `docs/ASSUMPTIONS.md`: 가정

# 개발

```bash
uv sync
uv run pytest -q                             # 약 7분
uv run ruff check . && uv run ruff format --check .
uv run python devtools/make_examples.py      # docs/examples/*.log 재생성
uv run python devtools/make_catalog_doc.py   # docs/CATALOG.md 재생성
uv run python devtools/run_doc_commands.py   # 사용자 문서의 명령을 실행해 기록
shellcheck bootstrap.sh
```

# 공개 전 점검

- [ ] `LICENSE`(MIT) 저자·연도 확인
- [x] README의 저장소 주소를 실제 주소로 교체
- [x] 시험 전에 PR을 `main`에 병합 (한 줄 설치는 `main`을 받는다). PR #10, 2026-11-09
- [ ] 저장소에 토큰·개인 경로·시험 관련 비공개 자료가 없는지 확인
- [ ] `docs/TEST_REPORT.md`가 최신인지 확인
