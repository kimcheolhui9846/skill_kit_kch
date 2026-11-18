# 시험 환경과 v1 설치

시험 중에는 운영 환경이 제공하는 에이전트와 공식 규칙을 따릅니다. Claude Code는 시험 전 개발에만 사용하세요. 이 설치기는 정책과 스킬 파일을 배치하며 외부 모델을 호출하지 않습니다. 키트를 미리 받아 두면 `--offline`으로 네트워크 없이 설치할 수 있습니다.

아래는 Codex 전용 v1 절차입니다. 일반 개발용 설치는 [설치 가이드](INSTALL.md), v2로 옮기는 방법은 [마이그레이션 가이드](MIGRATION_V1_TO_V2.md)를 보세요.

## 시험 당일 설치

코파 원격 환경 시험에서는 **방법 1**을 쓴다. 명령은 미리 복사해 두거나 메모에 띄워 둔다. 원격 환경에서 GitHub 접속, Python, Node가 되는지는 사전 체험 때 [사전 체험 체크리스트](../RULES_CHECKLIST.md)로 확인한다.

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

미검증(자동 문서 기록). 공개 저장소에서 받는 명령은 네트워크가 필요하다.

이미 받아 둔 키트가 있으면 clone 대신 갱신한다. 그래서 두 번 실행해도 "already exists"로 멈추지 않는다.

`--target`을 빼면 현재 폴더에 설치한다. 프로필은 끝에 `--profile python`처럼 붙인다. 이 방법은 당일 GitHub에 접속할 수 있어야 한다.

#### 방법 2. 개인 노트북에 미리 세팅하고 함수로 호출

**코파 플랫폼 시험에는 쓸 수 없다.** 시험은 코파가 제공하는 원격 환경의 Codex에서 진행되므로 노트북 설정이 넘어가지 않는다. 시험 당일에는 방법 1을 쓴다. 이 방법은 본인 PC에서 연습하거나, Codex를 로컬에서 직접 쓰는 경우를 위한 것이다.

시험 전에 노트북에서 한 번만 한다. 미검증(자동 문서 기록). 원격 복제와 PowerShell 프로필 등록은 직접 한다.

1. git, Python 3.9 이상, Codex를 설치한다. MCP를 쓰려면 Node.js도 설치한다.
2. 키트를 고정 위치에 받는다.
   ```powershell
   git clone https://github.com/kimcheolhui9846/skill_kit_kch C:\kit
   ```
3. PowerShell 프로필에 함수를 등록한다. `notepad $PROFILE`로 열고(파일이 없으면 먼저 `New-Item -ItemType File -Force $PROFILE`) 아래를 붙여 넣는다.
   ```powershell
   function kit { python C:\kit\run_kit.py @args }
   function kit-update { git -C C:\kit pull --ff-only }
   ```
4. PowerShell을 새로 열고 빈 폴더에서 `kit`을 실행해 `Status: READY`가 나오는지 확인한다.

시험 전날 `kit-update`로 최신 버전을 받아 둔다. 당일에는 작업 폴더에서 `kit --offline`을 실행한다. 키트를 작업 폴더와 나란히 받았다면 아래 명령으로도 오프라인 설치할 수 있다.

```bash
python ../skill_kit_kch/run_kit.py --offline
```

#### 설치 뒤 공통 확인

1. Codex를 **키트를 설치한 작업 폴더에서** 연다. 다른 폴더에서 열면 키트 Skill이 보이지 않는다.
2. 신뢰(trust) 확인창이 뜨면 신뢰를 고른다. MCP는 신뢰한 폴더에서만 켜진다. Skill과 AGENTS.md는 신뢰와 무관하게 읽힌다.
3. `/skills`로 키트 Skill을, `/mcp`로 `sequential-thinking`을 확인한다. 안 보이면 [사전 체험 체크리스트](../RULES_CHECKLIST.md)의 대체 경로를 따른다.
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

네트워크는 `python` 프로필이 pytest·ruff를 설치할 때(`uv tool install`, 실패하면 `pip install --user`)와 MCP 핸드셰이크(`npx -y`)에서만 쓴다. `core`와 `web`은 도구를 설치하지 않는다. 쓰는 경우 보고서의 `Network:` 줄에 표시한다. 자세한 내용은 [보안 정책](../SECURITY.md)를 본다.

### MCP

`python`, `data`, `web`, `full` 프로필(`data`와 `full`은 `python`을 상속한다)은 대상의 `.codex/config.toml`에 `sequential-thinking` 서버 하나를 등록한다(`npx -y @modelcontextprotocol/server-sequential-thinking@2026.8.31`, stdio). `fetch`, `git`, `filesystem`은 후보로 기록만 하고 등록하지 않는다(사유는 [보안 정책](../SECURITY.md)). 같은 프로필들이 `npx -y` 핸드셰이크도 한다. `full`은 도구 설치만 건너뛴다. 등록은 `# hackathon-kit:begin` … `# hackathon-kit:end` 구간 안에서만 이루어지며 전역 설정은 건드리지 않는다.

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

[예시 로그](../examples/)에는 설치, 재실행, 실패, 오프라인, 충돌 사례가 있다. `uv run python devtools/make_examples.py`로 네트워크 없이 다시 만든다.

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

- [사전 체험 체크리스트](../RULES_CHECKLIST.md): 사전 체험 체크리스트와 규칙
- [문제 해결](../TROUBLESHOOTING.md): 메시지별 대응
- [가정](../ASSUMPTIONS.md): 가정
