# 05 CLI 명세 (P2-T5)

- 기준: `00_PROMPT.md` §P2-T5, ADR-002/003/013/014/018/019/021, `04_DESIGN.md`
- 진입점은 `bootstrap.sh`, `bootstrap.ps1`, `python -m kit`(= `run_kit.py`) 세 가지이고, 모두 인수를 그대로 넘긴다(ADR-013). 아래 `kit`은 이 셋 중 하나를 뜻한다.

## 1. 분기 규칙 (ADR-002)

```
argv[0]이 아래 서브커맨드 이름 중 하나  → 새 경로(kit/commands.py)
그 밖의 모든 입력(빈 입력, --옵션, 알 수 없는 단어) → 기존 경로(kit/cli.py, 변경 없음)
```

- 서브커맨드 이름: `install plan verify doctor update uninstall restore profiles source capture task req trace report recover`
- 이 규칙이 기존 입력과 충돌하지 않는 근거: 기존 파서에는 위치 인수가 없다 [확인됨: `kit/cli.py:36-65`]. 따라서 기존 사용법에서 첫 토큰이 단어인 경우는 늘 오류(64)였다.
  - 예외는 첫 토큰이 서브커맨드 이름과 같은 오타 입력이다. 이전에는 64였고 이제는 새 경로로 간다. 이전에도 유효한 호출이 아니었으므로 호환성 문제는 없다.
- `kit --help`(기존 경로) 출력은 바꾸지 않는다. 새 서브커맨드 안내는 `kit help`(새 경로)와 README에 둔다.
  - 기존 `--help`의 EPILOG에 한 줄을 추가하는 것은 기준선 문자열 변경이므로 하지 않는다.

## 2. 기존 옵션 → 새 명령 대응표

| 기존 호출 | 같은 의미의 새 호출 | 비고 |
|---|---|---|
| `kit` | `kit install --agent codex --policy restricted --profile core` | 결과는 기존 경로와 바이트 동일(골든) |
| `kit --profile P` | `kit install --agent codex --policy restricted --profile P` | |
| `kit --target D` | `… --target D` | |
| `kit --dry-run` | `kit plan …` 또는 `kit install … --dry-run` | |
| `kit --offline` | `… --offline` | |
| `kit --verify-only` | `kit verify --agent codex …` | |
| `kit --no-mcp` | `… --no-mcp` | |
| `kit --verbose` | `… --verbose` | |

- 새 경로의 `install --agent codex --policy restricted`가 기존 경로와 같은 트리와 보고서를 만드는지는 골든 테스트로 확인한다(P3).
- 단, 새 경로의 보고서는 에이전트별 구간 형식(§5)이므로 보고서 문자열까지 같을 필요는 없다. 바이트 동일 요구는 **서브커맨드 없는 호출**에만 적용한다.

## 3. 공통 옵션 (새 경로)

| 옵션 | 뜻 | 기본값 |
|---|---|---|
| `--agent codex\|claude\|both` | 대상 에이전트 | `install`·`plan`·`verify`·`update`·`uninstall`에서 필수 |
| `--profile a[,b…]` | 프로필·팩 조합(ADR-007) | `core,hitl`(ADR-008) |
| `--policy standard\|restricted` | 정책 축(ADR-015) | `standard` |
| `--scope project\|user` | 설치 범위(ADR-018) | `project` |
| `--target DIR` | 작업 공간. `--scope user`와 같이 쓰면 64 | 현재 디렉터리 |
| `--dry-run` | 쓰지 않고 plan만 표시한다 | 끔 |
| `--offline` | 네트워크를 쓰지 않는다. 네트워크 항목은 SKIPPED | 끔 |
| `--yes` | 확인을 생략한다. 비대화형에서 네트워크·user 범위 작업에 필요(ADR-014) | 끔 |
| `--no-mcp` | MCP 항목 제외 | 끔 |
| `--mcp NAME` | `catalog/mcp.json`에서 기본으로 꺼진 서버를 켠다. 반복 가능. `--no-mcp`와 같이 쓰면 64. 목록만 있는 서버(버전 고정 없음)·모르는 이름·정책 밖·어느 에이전트에도 맞지 않는 이름은 64(P4-T5) | 없음 |
| `--hooks` | 승인 기록 훅 등록(ADR-011, opt-in) | 끔 |
| `--plugin ID` | 고위험 플러그인 선언을 명시적으로 켠다. 반복 가능(ADR-010). P4-T5: `catalog/plugins.json`의 이름이고, 항목의 `agents`에 든 에이전트에만 간다. Claude: `.claude/settings.json`에 선언하고, 네트워크 허용(`--yes` 또는 확인) 시 `claude` CLI로 이 PC에 설치한다(`~/.claude/plugins/`, `.claude/settings.local.json`에 씀). Codex: `.agents/plugins/marketplace.json`을 쓰고, 네트워크 허용 시 `codex` CLI로 설치한다(`~/.codex/plugins/`, `~/.codex/config.toml`에 씀, 모든 프로젝트에서 켜짐). `uninstall`이 각 CLI로 되돌린다 | 없음 |
| `--verbose` | 파일별 세부 표시 | 끔 |
| `--json` | 기계가 읽는 결과를 stdout에 출력한다(보고서 대신) | 끔 |
| `--report-json FILE` | 사람용 보고서는 그대로 두고 JSON을 파일에 쓴다 | 없음 |

## 4. 명령

### 4.1 설치 계열

```text
kit install   --agent A [--profile …] [--policy …] [--scope …] [--target DIR] [--dry-run] [--offline]
              [--no-mcp] [--mcp NAME]… [--hooks] [--plugin ID]… [--yes] [--verbose] [--json|--report-json FILE]
kit plan      (install과 같은 인수. 항상 쓰기 없음)
kit verify    --agent A [--scope …] [--target DIR] [--offline] [--no-mcp]
kit doctor    [--target DIR]                      # 읽기 전용: 설치된 에이전트 CLI·버전, 기존 키트 흔적, 프로필 추천
kit update    --agent A [--scope …] [--dry-run] [--yes]   # 키트 소유 항목만 현재 버전으로 갱신
kit uninstall --agent A [--scope …] [--dry-run] [--yes]   # 매니페스트 소유이고 해시가 같은 것만 삭제
kit restore   --backup <stamp> [--scope …] [--dry-run] [--yes]
kit profiles  list | show <a[,b…]> [--agent A]
```

- `--mcp`·`--plugin`으로 고른 것은 매니페스트 항목의 `opt_in`에 남는다. `verify`·`update`는 이 기록을 그대로 쓰므로 플래그를 다시 줄 필요가 없다. 한 번에 설치한 에이전트는 같은 `opt_in`을 기록하므로 `verify --agent both --json`은 JSON 문서 하나를 낸다.
- `--scope user`에서는 `--dry-run`이 아니면 항상 확인을 받는다. 비대화형이면 `--yes`가 필요하고, 없으면 64로 끝나며 이유를 출력한다(ADR-018).
- `install --scope user`의 plan은 파일별 diff를 보여 준다. `~/.codex/AGENTS.md`의 결과 크기가 28 KiB를 넘으면 경고를 함께 표시한다(R-10).
- `uninstall`과 `update`는 사용자가 고친 항목(해시 불일치)을 건드리지 않는다. 그런 항목은 `CONFLICT`로 보고한다.
  - P4-T7: `update`가 CONFLICT로 남긴 항목은 매니페스트에서 빠져 사용자 것이 된다. 그 뒤의 `uninstall`은 그 항목을 언급하지 않고 남겨 둔다.
- `--scope user` (P4-T7):
  - `--target`, `--plugin`과 같이 쓰면 64다. 현재 위치가 home 자체인데 `--scope project`이면 65다.
  - 확인 프롬프트는 dry-run과 같은 계획을 비밀값을 가린 채 보여 주고 `y`/`yes`만 승인으로 본다.
  - Claude의 MCP 줄은 `N to add by hand (claude mcp add --scope user)`이고, Manual checks에 서버별 명령이 나온다. `~/.claude.json`은 쓰지 않는다.
  - JSON의 `target`은 `"~"`, `scope`는 `"user"`다.
- 원문의 `migrate`는 **두지 않는다**(ADR-003).

### 4.2 소스 계열 (ADR-021)

```text
kit source list   [--json]
kit source add    <github-url|owner/repo> [--ref R] [--path P]… [--all] [--name N] [--pack K]
                  [--accept-license] [--yes] [--json]
kit source check  [--online] [--yes] [--json]
kit source update <id> [--ref R] [--yes] [--json]
kit source remove <id> [--yes]
```

- **이름을 통일한다:** 명령은 `source`(단수)로 하고, 원문의 `sources verify --offline`은 `source check`로 대신한다.
  - 기본은 오프라인 검사다: 로컬 해시와 LICENSE 파일이 있는지 확인한다.
  - `--online`을 주면 원격 커밋이 존재하는지도 확인한다. 이것은 네트워크 동작이므로 D-14 확인을 거친다.
- `add`·`update`는 네트워크를 쓴다. `--offline`과 함께 주면 64다.
- `--accept-license`는 라이선스가 `other`인 경우에만 효과가 있다. 라이선스가 없거나 copyleft인 경우에는 무시하고 `referenced`로 처리한다(ADR-009).
- **P4-T8 구현 (`kit/source_add.py`, `kit/source_cli.py`, `kit/github_fetch.py`, `kit/source_scan.py`):**
  - `add`의 추가 옵션:
    - `--include PATH`: 기본으로 빼는 스크립트(`.sh .ps1 .py .js` 등)를 파일 단위로 넣는다.
    - `--replaces SKILL` / `--keep-both`: 겹침 판정에 대한 결정.
    - `--accept-risk`: REVIEW 판정(원격 스크립트 실행 한 줄, 숨은 유니코드, 프롬프트 인젝션 문구)을 사람이 확인했다는 표시. lock의 `risk`가 medium이 되고 `verification.notes`에 남는다.
    - `--overlap-threshold F`: 기본 0.5.
  - `update`도 `--accept-license`, `--accept-risk`를 받는다. `--offline`과 함께 주면 64다.
  - `--yes`가 없으면 터미널에서 `Apply? [y/N]`을 묻는다. 터미널이 없거나 `--json`이면 계획만 내고 0으로 끝난다.
  - 출력 줄: `Source:`(owner/repo @ ref -> 커밋 12자), `Id:`, `Kind:`, `License:`(→ vendored-verbatim 또는 referenced), `Files:`(CREATE/UPDATE/UNCHANGED/DELETE/LEFT OUT), `Catalog:`, `Overlap:`, `Findings:`(BLOCK/REVIEW/WARN), `Note:`, `Status:`, `Next action:`.
  - 종료 코드:
    - 1: BLOCK 판정(비밀값, 바이너리, 공식 스킬 제약 위반, 기존 파일과 내용 충돌, 스킬 폴더 안의 링크, 경로 탈출, 크기 초과), 반영 중 실패(모두 되돌림).
    - 2: REVIEW 판정, 겹침 결정 필요, 이름 충돌, 스킬 여러 개인데 `--path`/`--all` 없음, 종류 판별 불가, 같은 주소의 다른 커밋(`update` 안내), 손으로 넣은 항목과 같은 폴더, 로컬에서 고친 파일의 `update`, 네트워크 실패.
    - 65: 없는 저장소·ref·경로, `remove`/`update`의 없는 id, `check`의 lock 손상.
  - `remove`·`update`는 `kit source add`로 들어온 항목(`added_by: "source add"`)만 다룬다. 손으로 넣은 항목은 2로 끝난다. 프로필이나 팩이 그 스킬 이름을 직접 적고 있어도 `remove`는 2로 끝난다.
  - `check`는 오프라인 검사가 기본이다. `--online`은 고정 커밋이 GitHub에 있는지 확인한다. `--yes`나 터미널 승인이 없으면 SKIPPED이고, 종료 코드는 오프라인 결과를 따른다.
  - `list [--json]`은 id, 종류, 반영 방식, 라이선스, 커밋, 출처를 보여 준다.
  - **큰 저장소(2026-11-06, U-40).** 저장소 전체 압축본이 `MAX_BYTES`(20 MiB)를 넘고 `--path`가 있으면, GitHub API의 트리 목록(`git/trees/<커밋>?recursive=1`)에서 고른 폴더의 파일과 그 위 폴더들의 라이선스 파일만 하나씩(`git/blobs/<sha>`) 받는다. 압축본과 같은 규칙을 쓴다: 경로 탈출과 서브모듈 같은 특수 항목은 1, 링크는 기록, 고른 파일 합계도 `MAX_BYTES`까지, 받은 크기가 목록과 다르면 1. 트리 목록이 잘리면(truncated) 1이다. `--path`가 없으면 `…; name the folders with --path`로 1이다. 접속하는 호스트는 그대로 `api.github.com`뿐이다.
  - 스킬의 `SKILL.md` frontmatter `license`가 찾은 라이선스 파일과 다르면 `Note:` 줄로 보여 준다(판정은 라이선스 파일 기준 그대로).

### 4.3 capture (ADR-019)

```text
kit capture [--agent codex|claude|both] [--write] [--json]
```

- 기본은 dry-run이다: 무엇을 어디로 가져올지, 무엇을 가렸는지를 표시한다.
- `--write`를 주면 `user/`에 쓴다.
- 비밀값 스캔에 하나라도 걸리면 아무것도 쓰지 않고 1로 끝난다. 출력에는 키 이름과 파일 위치만 나오고 값은 나오지 않는다(R-09).
- 출력(P4-T7): `Files:`(CREATE/UPDATE/UNCHANGED + 저장소 경로), `Left out:`(뺀 섹션·표·최상위 키, 개수만), `Secret scan:`(clean 또는 `파일: 종류 (line N)`), `Status:`, `Next action:`. `--json`은 `written`, `files`, `left_out`, `secret_hits`를 낸다.
- 허용 목록은 `user/capture-allowlist.json`(04 §3.8)이다. 키트 구간은 capture하지 않는다.
- **내 파일로 가져오기(Q4, 검토자 결정 2026-11-06).** 허용 목록 `codex.copy.skills`·`codex.copy.prompts`에 적은 이름만 `~/.codex/{skills,prompts}/`에서 `user/codex/own/{skills,prompts}/`로 바이트 그대로 복사한다(비밀값 스캔 포함). 링크이거나 없으면 `Left out:`에 `not found (or a link)`, UTF-8이 아니면 `not UTF-8 text`. 목록에서 빠진 파일은 다음 capture에서 `REMOVE`다. inventory의 출처는 `carried as your own (user/codex/own/…)`. `install --scope user`(Codex)는 이 파일들을 `~/.codex/`에 키트 소유로 쓰고, `verify`에 `own` 항목이 생긴다. 같은 내용이 이미 있으면 소유하지 않고 둔다. 키트·OMX 스킬과 이름이 겹치면 64다.
- **실행 기록(2026-11-06).** 검토자 승인("변경 목록 먼저 보고 쓰기" → "쓰기") 후 이 PC에서 `kit capture --agent both --write`를 실행했다. 비밀값 스캔 clean, `user/`에 14개 파일(스냅숏 7개 + own 7개). 커밋은 하지 않았다.

### 4.4 HITL 계열 (원문 그대로, 세부는 P5에서)

```text
kit task    add | list | start | submit | approve | request-changes | status
kit req     add | list | impact <REQ-ID>
kit trace   check
kit report  tests --junit FILE [--out FILE]
kit recover
```

- `task approve`는 TTY에서 Task ID를 다시 입력받아야 성공한다. 이 경우 `by: human-cli`로 기록된다.
- 비대화형에서는 `--by agent-recorded --quote "<사용자 발화 원문>"`이 있어야 하고, 이 경우 `by: agent-recorded`로 기록된다(04_DESIGN §3.3).
- `--hooks`로 설치된 훅이 사용자 프롬프트에서 승인을 기록하면 `by: human-hook`이다.

**P5-T2 구현(L1).** 모든 동작은 `--target DIR`과 `--json`을 받는다.

```text
kit task add <ID> --title T [--requires REQ-001]... [--depends-on <ID>]... [--grade L|S|C]
kit task list
kit task start <ID>
kit task subtask add <ID> "<제목>" | kit task subtask done <ID>.<n>
kit task report <ID> [--force]          # .kit/work/reports/<ID>.md에 §5.6 템플릿
kit task submit <ID> [--report FILE]
kit task approve <ID> [--by human-cli|agent-recorded] [--quote|--evidence "<발화 원문>"]
kit task request-changes <ID> --reason "<이유>"
kit task status [<ID>]
```

- 종료 코드: 0 완료, 1 `status`에 경고(승인 뒤 보고서 변경·삭제), 2 규칙이 거부함(`Refused:` 뒤에 이유, `Status: BLOCKED`), 64 인수 오류, 65 `tasks.json`·`trace.json` 손상.
- 2가 되는 경우: 선행 Task가 APPROVED가 아님, 다른 Task가 IN_PROGRESS, 상태가 맞지 않는 전이, 끝나지 않은 Subtask, 보고서 검사 실패, submit 뒤 바뀐 보고서, TTY 없는 human-cli, 다시 입력한 ID 불일치, 작업 공간 밖 보고서 경로.
- 64가 되는 경우: `--by human-hook`(훅만 쓴다), human-cli에 `--quote`, agent-recorded에 `--quote` 없음, id·REQ·grade 형식.
- 보고서 테스트 표: 요구사항 열에 must REQ가 있는 행이 하나 이상 있어야 한다. 실행하지 않은 테스트는 `NOT RUN: <이유>`로 쓴다. 이유 없는 `NOT RUN`은 거부된다.

### 4.5 기타

```text
kit help [<command>]
kit version
```

## 5. 보고서 형식

**기존 경로:** 기준선과 같다(`docs/v2/baseline/install-snapshots/`).

**새 경로:** 에이전트별 줄을 추가한다.

```text
Target:       D:\work\app
Scope:        project
Profiles:     core, hitl   Policy: standard
Agent codex:  AGENTS.md INSTALLED | Skills 13/13 verified | MCP 1 registered | Load UNVERIFIED (run /skills in Codex)
Agent claude: CLAUDE.md INSTALLED | Skills 13/13 verified | MCP 1 declared  | Load UNVERIFIED (run /skills in Claude Code)
Hooks:        not installed (opt-in: --hooks)
Manual steps: 1 (see below)
Network:      not used
Status:       READY
Next action:  …
```

- `--scope user`이면 `Target:` 줄 대신 `Home: ~`를 쓴다. 경로는 `~`로 줄여 표시한다(R-09: 사용자 이름이 노출되는 것을 줄임).
- 프로필의 `recommended_policy`와 다른 정책으로 설치·계획하면 `Profiles:` 줄 아래에 `Warning:      profile 'hackathon' is meant for --policy restricted …`가 나오고, JSON에는 최상위 `policy_warnings` 배열이 있다(ADR-015, P4-T6). 설치는 그대로 진행한다.
- `Manual steps:`가 0보다 크면 그 아래에 명령을 번호와 함께 출력한다. Claude user MCP, OMX 자체 설치, 플러그인 `/plugin`이 여기에 해당한다.
- 에이전트별로 실제 로드되는지는 키트가 확인할 수 없으므로 항상 `UNVERIFIED`로 표시하고, 수동 확인 절차를 안내한다.
- **API 키 안내(P4-T9).** 고른 MCP 서버·플러그인·스킬 중 카탈로그에 `credentials`가 있는 것이 있으면 `plan`(DRY RUN 줄 앞), `install`·`verify`·`update`(Status 줄 앞)에 한 절이 나온다. 없으면 절 자체가 없다.

  ```text
  API keys (set later; the kit never asks for, stores or prints a key):
    ANTHROPIC_API_KEY  [optional, not set]  LLM review of git diffs on stop; …
      used by:  plugin security-guidance (claude)
      get it:   https://platform.claude.com/settings/keys  (pay per use)
      set it:   PowerShell  [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "<your key>", "User")
                bash/zsh    add  export ANTHROPIC_API_KEY="<your key>"  to ~/.bashrc or ~/.zshrc
    Then open a new terminal and restart the agent; `kit verify` shows set / not set.
  ```

  - 키 하나에 한 항목이고, 같은 키를 쓰는 항목은 `used by`에 모은다. 어느 하나라도 필수면 `required`다.
  - 필수 키가 `not set`이면 `Next action`에 `- Set NAME (see API keys above), open a new terminal and restart the agent.`가 붙는다. 상태와 종료 코드는 바뀌지 않는다.
  - JSON(`plan --json`, 보고서 JSON)은 최상위 `api_keys` 배열에 `env, required, set, purpose, get_it, cost, used_by`를 담는다. 값은 없다.
  - 로그 마스킹은 그대로이며, 값이 아닌 두 가지만 마스킹하지 않는다: 안내 문구의 자리표시자 `"<your key>"`, 환경 변수 참조 `${NAME}`(작은따옴표 포함 가능, 예: `-e 'NAME=${NAME}'`). 그 뒤에 다른 글자가 붙으면 예전처럼 마스킹한다.
- **팩만 고른 경우의 경고(P5-T1 §8-1, 검토자 결정 2026-11-06).** standard 정책의 스킬 안내 절이 이름을 든 스킬 중 이번 설치에 없는 것이 있으면 에이전트마다 `Warning: the standard policy names skills this install leaves out: …; add --profile core (or a profile that lists them)`가 나온다(JSON은 에이전트의 `warnings`). 종료 코드는 바뀌지 않는다. restricted는 안내 절이 없어 경고도 없다.
- **수동 안내 `--manual NAME`(U-23, 검토자 결정 2026-11-06).** `install`·`plan`에서 `catalog/manual.json`의 도구를 고르면 `Manual guides (the kit runs none of this; you decide and run it):` 절에 버전·위험·라이선스·네트워크·파일, 번호 붙은 단계, `undo`, `docs`가 나온다(DRY RUN·Status 줄 앞). JSON은 최상위 `manual_guides`. 키트는 아무것도 실행·설치·기록하지 않으며 매니페스트에도 남기지 않는다(`verify`·`update`에는 나오지 않음). 모르는 이름, 고른 에이전트·정책에 맞지 않는 이름은 64다.

## 6. 종료 코드

기존 5개를 그대로 쓰고 **새 코드는 만들지 않는다.**

| 코드 | 이름(`kit/model.py`) | 새 경로에서의 뜻 |
|---|---|---|
| 0 | READY | 완료, 또는 dry-run/plan 표시. 검사 명령이면 모두 PASS |
| 1 | PARTIAL | 일부 실패, 검사 FAIL(`verify`, `source check`, `trace check`), 비밀값 스캔 적중(`capture`), 소스 보안 검사 차단 |
| 2 | BLOCKED | `CONFLICT`, `NEEDS_HUMAN`(소스 종류 판별 불가, 로컬 수정된 vendored 파일 update), 네트워크 필요 작업의 네트워크 실패, 예상치 못한 예외 |
| 64 | USAGE | 잘못된 인수, 조합 오류(`--scope user` + `--target`, `add` + `--offline`), 비대화형인데 `--yes` 없이 user 범위 쓰기, 셸 전용 모드에서 서브커맨드 사용 |
| 65 | TARGET | 대상 오류(없는 경로, 키트 자신, 쓸 수 없는 HOME), 입력 데이터 오류(알 수 없는 상위 schema, 없는 GitHub 저장소) |

명령별 요약:

| 명령 | 0 | 1 | 2 | 64 | 65 |
|---|---|---|---|---|---|
| install/update | 완료 | 일부 항목 실패 | 충돌·차단 | 인수 | 대상 |
| plan/doctor/profiles/list | 항상(오류 제외) | — | — | 인수 | 대상·schema |
| verify | 모두 PASS | FAIL 있음 | 검사 불가 | 인수 | 대상 |
| uninstall/restore | 완료 | 일부 남음 | 사용자 수정 항목 있음 | 인수 | 백업 없음 |
| source add/update | 완료·plan | 보안·형식 차단 | NEEDS_HUMAN·네트워크 실패 | 인수 | 저장소 없음 |
| source check | 일치 | 불일치 | 네트워크 실패(`--online`) | 인수 | lock 손상 |
| capture | 완료·dry-run | 비밀값 적중 | 읽기 실패 | 인수 | HOME 없음 |
| task/req/trace/report/recover | 완료 | 검사 실패(trace) | 상태 전이 거부(미승인 선행 Task) | 인수 | 작업 파일 손상 |

## 7. `--agent both`의 실행 순서와 실패 처리

1. 두 Adapter의 plan을 **먼저 모두** 계산한다. 이 단계는 순수 계산이며 쓰기가 없다.
2. 같은 경로에 쓰는 Action이 두 Adapter에서 겹치면 64로 끝난다. 정상 설계에서는 생기지 않는다.
3. 확인과 백업은 한 번에 한다(하나의 `<stamp>`).
4. 적용 순서는 codex → claude다.
5. 적용 중 어느 한쪽에서 쓰기가 실패하면 **이번 실행 전체**를 백업으로 되돌린다. 두 에이전트 모두 되돌리며, 한쪽만 설치된 중간 상태를 남기지 않는다.
6. 쓰기 실패가 아닌 검사 실패는 되돌리지 않는다. 예: verify FAIL, 네트워크 SKIPPED. 전체 상태는 두 에이전트 중 **가장 나쁜 상태**(2 > 1 > 0)를 따른다.

## 8. 셸 전용 모드(Python 없음)

- 원문 권장안: `install --agent claude`의 최소 복사만 지원한다.
- **이 명세의 결정:** 셸 전용 모드에서는 서브커맨드를 지원하지 않는다(ADR-013).
- 첫 토큰이 서브커맨드 이름이면 다음을 출력하고 64로 끝난다.
  ```
  error: '<cmd>' requires Python 3.9+ (shell-only mode supports only the legacy install)
  ```
  - 이전에도 같은 입력은 `error: unknown argument: <cmd>`와 함께 64였다 [확인됨: `bootstrap.sh:79-82`]. 종료 코드는 그대로이고 메시지만 더 구체적으로 바뀐다.
  - 기존 테스트에는 이 메시지를 단언하는 곳이 없다 [확인됨: `tests/test_entrypoints.py`에서 "unknown" 검색 결과 0건].
- 원문과 다르게 정한 이유:
  - 셸 모드에서 Claude용 복사를 구현하려면 `bootstrap.sh`와 `bootstrap.ps1` 두 곳에서 카탈로그를 해석해야 한다. 그러면 로직이 중복되고 R-3 같은 위험이 다시 생긴다.
  - Claude Code를 쓰는 환경에는 사실상 Python이 있다고 가정한다 [가정].

## 9. 출력과 로그 규칙

- 사람용 출력은 stdout, 오류는 stderr로 보낸다. `--json`이면 stdout에는 JSON 하나만 출력한다.
- 로그는 project 범위에서 `.kit/logs/`, user 범위에서 `~/.kit-state/logs/`에 쓴다. 기존 마스킹(`kit/logs.py:10-26`)을 적용하고, 토큰 패턴은 `kit/secrets_scan.py`와 같은 목록을 쓴다.
- 네트워크를 쓰는 모든 Action은 plan과 보고서의 `Network:` 줄에 에이전트별로 표시한다(D-14).
