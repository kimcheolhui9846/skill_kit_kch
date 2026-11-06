# 04 설계

- 기준: `00_PROMPT.md` §P2-T2~T4, `00_ADDENDUM.md`, ADR-001~021(`docs/v2/adr/`)
- 진행 상태:
  - §1(P2-T2): 승인(2026-11-05)
  - §2(P2-T3 Adapter), §3(P2-T4 데이터 모델): 완료(2026-11-05)

## 1. 디렉터리 구조 (P2-T2)

### 1.1 확정 구조

`[기존]`은 그대로 두는 것, `[신규]`는 새로 만드는 것이다. 기존 파일은 **옮기거나 이름을 바꾸지 않는다**(ADR-001, ADR-002).

```text
skill_kit_kch/
├── AGENTS.md                         [기존] 키트 레포 자체 정책. 기존 경로 설치 원문(바이트 동일 유지)
├── .agents/skills/<11개>/            [기존] 기존 11개의 원본이자 restricted·셸 모드 설치 세트. 새 스킬 추가 금지(ADR-001, V-22)
├── bootstrap.sh / bootstrap.ps1      [기존] 진입점. 서브커맨드는 Python 경로로 넘긴다(ADR-013)
├── run_kit.py, pyproject.toml        [기존] package = false 유지
├── profiles/                         [기존] core/python/web/data/full.json(v1, 내용 불변)
│   ├── fullstack.json ai-research.json hackathon.json   [신규] v2 스키마(ADR-007)
│   └── packs/                        [신규] hitl.json verify-plus.json launch.json …(ADR-008)
├── mcp/                              [기존] manifest.json, allowlist.json(스키마는 하위 호환으로 확장)
├── catalog/                          [신규] 새 경로의 설치 목록
│   ├── skills.json                   스킬 이름 → 위치(.agents/skills | shared/skills | third_party/…), 팩, 에이전트
│   ├── mcp.json                      에이전트별 MCP 매핑(버전 고정, enabled_by_default)
│   └── plugins.json                  플러그인 선언 카탈로그(ADR-010, 고위험 = enabled_by_default:false)
├── shared/                           [신규]
│   ├── README.md                     스킬 위치 3곳을 표로 설명(ADR-001 위험 대응)
│   ├── skills/<name>/                키트가 작성한 새 경로용 스킬
│   │                                 (launch-compliance-check, add-skill-source, data-quality-validator, HITL 스킬)
│   ├── skills/overlays/<name>/       기존 스킬의 standard 경로용 확장(Q7: counterexample-hunter, algorithm-options)
│   ├── policies/                     정책 원문 모듈(ADR-004): core.md light-path.md skills.md testing.md hitl.md
│   │   └── environments/standard.md  (restricted 원문은 루트 AGENTS.md, P4-T6)
│   ├── hooks/approval_hook.py        L2 승인 기록 훅. 두 에이전트 공용(ADR-011)
│   ├── workflows/                    HITL 템플릿: task-report.md handoff.md adr.md
│   └── evaluation/                   trace·반례·보고 스키마와 템플릿
├── codex/                            [신규] 에이전트 전용 조각(있을 때만)
│   ├── policies/                     Codex 전용 정책 조각(도구 이름, /skills 안내)
│   └── hooks.json                    approval_hook 등록 형식(opt-in)
├── claude/                           [신규]
│   ├── policies/                     Claude 전용 정책 조각
│   └── settings.hooks.json           approval_hook 등록 형식(opt-in)
├── user/                             [신규] user 범위 스냅샷(REQ-USER-001, ADR-018/019)
│   ├── capture-allowlist.json        capture가 가져올 키·파일(허용 목록)
│   ├── codex/                        AGENTS.block.md, config.toml(표), mcp.json(이름), inventory.json — ${HOME} 템플릿
│   └── claude/                       CLAUDE.block.md, settings.json(소유 키), mcp.json(이름·전송 방식)
├── third_party/<owner>-<repo>/       [신규] vendored 외부 텍스트 + LICENSE(ADR-009, ADR-021)
│   └── Yeachan-Heo-oh-my-codex/      OMX 스킬 29개, prompts 32개(REQ-USER-005). agents/*.toml은 태그에 없음
├── kit/                              [기존 모듈 유지]
│   ├── cli.py app.py …               [기존] 서브커맨드가 없는 경로는 변경하지 않는다(ADR-002)
│   ├── commands.py                   [신규] 첫 토큰 분기와 서브커맨드 파서
│   ├── adapters/ base.py codex.py claude.py registry.py   [신규] §2
│   ├── writers/ markdown_block.py toml_block.py json_keys.py   [신규] 기존 agentsmd/mcpconfig에서 추출(ADR-005)
│   ├── manifest.py                   [신규] .kit/state/install-manifest.json, v1 인수(ADR-006)
│   ├── policy_render.py              [신규] ADR-004
│   ├── userscope.py capture.py       [신규] ADR-018, ADR-019
│   ├── secrets_scan.py               [신규] capture·source·테스트가 공용으로 쓰는 스캐너
│   ├── sources/ lock.py fetch.py detect.py license.py scan.py overlap.py   [신규] ADR-021
│   └── workflow/ tasks.py trace.py junit.py counterexamples.py handoff.py recover.py   [신규]
├── devtools/                         [기존] make_examples.py
│   ├── snapshot.py                   [신규] baseline/install-snapshots/snapshot.py를 옮김(03_PLAN P3-T1)
│   └── manual_verify.sh / .ps1       [신규] Linux·pwsh7·Python 3.9 수동 검증(ADR-017)
├── tests/                            [기존 유지] + golden/ adapters/ workflow/ sources/ userscope/ fixtures/
├── docs/                             [기존 유지] + v2/, guides/
├── sources.lock.json                 [신규] 외부 소스 고정 기록(ADR-021 §6 형식)
└── THIRD_PARTY_NOTICES.md            [기존] 항목 추가
```

### 1.2 원문 권장 구조와 다른 점

| 원문 | 확정 | 근거 |
|---|---|---|
| 루트 `AGENTS.md`, `.agents/skills/`는 생성된 호환 미러 | **원본**으로 유지하고 생성하지 않는다. `devtools/sync_mirror.py`도 만들지 않는다 | ADR-001 |
| `shared/skills/overlays/{codex,claude}/` | `shared/skills/overlays/<name>/`. 에이전트별 차이가 아니라 **경로별 확장**(standard용)이다. 에이전트별 차이는 Adapter의 `render_skill`이 처리한다 | Q7, ADR-001 |
| `codex/skills/ mcp/ plugins/`, `claude/skills/ mcp/ plugins/` | MCP·플러그인은 `catalog/` 한 곳에서 에이전트 필드로 구분한다. **스킬은 트리 계층으로 둔다(P4-T1, 2026-11-06 사용자 요청):** 공통 원본(base) → 정책 overlay → `codex/skills/<name>/`·`claude/skills/<name>/`(에이전트 층). 위 층은 파일을 추가하거나 같은 경로를 대체하고, `<path>.append`는 아래 층 파일 끝에 붙인다. 에이전트 전용 스킬은 `location` 없이 해당 에이전트 층에만 둔다. 설명: `shared/README.md` | 공통은 한 번, 차이만 에이전트별로 |
| `claude/hooks/` | `shared/hooks/`에 스크립트를 하나 두고, 등록 형식만 에이전트별로 둔다 | ADR-011(두 에이전트 opt-in) |
| `kit/sources.py` | `kit/sources/` 패키지 | ADR-021 파이프라인 단계별 모듈 |
| (없음) | `user/`, `catalog/`, `kit/userscope.py`, `kit/capture.py`, `kit/secrets_scan.py` | REQ-USER-001~005, REQ-SRC-009 |
| `migrate` 관련 모듈 | 없음 | ADR-003 |

### 1.3 이동·삭제

- **없음.** 기존 파일은 옮기지도 지우지도 않는다(중간 승인 조건 A.3-2에 해당하지 않음).
- 문서 산출물 하나만 옮긴다: `docs/v2/baseline/install-snapshots/snapshot.py` → `devtools/snapshot.py`. 이것도 P3-T1에서 원본을 남긴 채 복사하는 방식으로 한다.

### 1.4 불변 조건(테스트로 강제)

| 불변 조건 | 테스트 |
|---|---|
| `.agents/skills/`는 기준선 11개와 이름·해시가 같다 | V-22 |
| `profiles/{core,python,web,data,full}.json`은 기준선과 같다 | 골든(P3-T1) |
| `user/` 아래에는 비밀값, `projects.*` 경로, auth 파일이 없다 | V-20 |
| `third_party/` 아래 각 항목에는 LICENSE가 있고 `sources.lock.json`의 vendored 항목과 1:1로 대응한다 | V-24 |
| 런타임 코드(`kit/`)는 표준 라이브러리만 import한다 | 기존 테스트 확장(R-08) |

## 2. Adapter 설계 (P2-T3)

### 2.1 계층

```
CLI(kit/commands.py)
  └─ 해석: ResolvedProfile(§3.2) + Context(target, home, scope, agent, policy, offline, yes)
       └─ Adapter(codex | claude).plan(...) → list[Action]          # 순수 함수, 쓰기 없음
            └─ 공통 실행기: 확인 → 백업 → writers → 원자적 쓰기 → 매니페스트 → 실패 시 롤백
                 └─ Adapter.verify(...) → list[CheckResult] → 기존 report 형식
```

- 기존 경로(서브커맨드 없음)는 P3-T1 골든 테스트가 생기기 전까지 `kit/app.py`를 그대로 둔다. 골든 테스트가 생긴 뒤 내부만 `CodexAdapter(policy=restricted, scope=project)`로 옮긴다. 옮기는 커밋에서 골든이 바뀌면 안 된다(ADR-002, R-1).
- `both`는 별도 Adapter를 두지 않고 두 Adapter의 Action을 합쳐 실행한다. 같은 경로에 쓰는 Action이 둘 생기면 plan 단계에서 오류(64)다.

### 2.2 인터페이스 (Python 3.9, `typing.Protocol`)

```python
class AgentAdapter(Protocol):
    name: str                                                    # "codex" | "claude"
    def detect(self, ctx: Context) -> AgentEnv: ...              # CLI·버전 탐지, 네트워크 없음
    def policy_target(self, ctx: Context) -> PolicyTarget: ...   # 경로 + 마커 형식(hackathon-kit, ADR-003)
    def skill_root(self, ctx: Context) -> PurePosixPath: ...     # scope에 따라 다름(표 2.3)
    def render_skill(self, skill: SkillSource, ctx: Context) -> list[FileSpec]: ...
    def mcp_writer(self, ctx: Context) -> ConfigWriter: ...      # toml_block | json_keys | manual
    def plugin_writer(self, ctx: Context) -> ConfigWriter: ...   # ADR-010
    def hook_writer(self, ctx: Context) -> Optional[ConfigWriter]: ...   # ADR-011 opt-in
    def plan(self, profile: ResolvedProfile, ctx: Context) -> list[Action]: ...
    def verify(self, profile: ResolvedProfile, ctx: Context) -> list[CheckResult]: ...
    def manual_checks(self, ctx: Context) -> list[str]: ...      # 사람이 에이전트 안에서 할 확인
```

- `Context`는 `target`, `home`, `scope`(`project|user`), `policy`, `offline`, `assume_yes`, `kit_root`를 갖는다. 테스트는 `home`을 주입해 HOME을 격리한다(V-19).
- 런타임에 평가되는 주석에는 `X | None`을 쓰지 않는다(3.9 호환, ADR-017).

### 2.3 에이전트별 매핑

| 항목 | Codex, project | Codex, user | Claude, project | Claude, user |
|---|---|---|---|---|
| 정책 파일 | `AGENTS.md` 구간 | `~/.codex/AGENTS.md` 구간. 28 KiB 넘으면 경고(Codex 기본 32 KiB) | `CLAUDE.md` 구간(ADR-004 렌더) | `~/.claude/CLAUDE.md` 구간 |
| 스킬 | `.agents/skills/<n>/` | `~/.codex/skills/<n>/`(Q5) | `.claude/skills/<n>/` | `~/.claude/skills/<n>/` |
| MCP | `.codex/config.toml` 구간 | `~/.codex/config.toml` 구간 | `.mcp.json` `/mcpServers/<n>` 소유 키 | **ManualStep**: `claude mcp add --scope user …` 출력(ADR-018) |
| 플러그인 | config.toml 구간 `[plugins."x@m"]` | 같음(user 파일) | `.claude/settings.json` `/enabledPlugins/<id>`, `/extraKnownMarketplaces/<m>` | `~/.claude/settings.json` 같은 키 |
| 훅(opt-in) | Codex 훅 설정의 키트 항목 [가정: 파일 위치는 P3-T4에서 CX-HK로 재확인] | 같음(user) | `.claude/settings.json` `/hooks/…` 원소 해시 | `~/.claude/settings.json` |
| 추가(OMX) | — | `~/.codex/skills/<omx>/`, `~/.codex/prompts/*` 파일 소유 | — | — |
| 수동 확인 | `/skills`, `/mcp` | 같음 | `/skills`, `/mcp`, `/plugin` | 같음 |

**P4-T7 확정(검토자 결정 2026-11-06: 스냅샷 + OMX + 키트 스킬):**
- user 범위의 정책 구간에는 키트 정책(10원칙)이 아니라 `user/<agent>/*.block.md`(이 PC에서 capture한 개인 전역 지침)가 들어간다. 키트 정책은 프로젝트 범위에만 둔다.
- 프로필의 키트 스킬은 두 에이전트 모두 설치한다. OMX는 Codex만이다.
- `~/.codex/config.toml` 구간에는 카탈로그 MCP 서버와 capture한 표(`[features]`, `[plugins."…"]`)가 들어간다. 같은 표가 구간 밖에 같은 값으로 있으면 빼고 알린다. 다른 값이면 CONFLICT(선택 항목이라 PARTIAL)이고 파일은 그대로 둔다. 카탈로그 서버가 구간 밖에 이미 정의돼 있어도 CONFLICT다.
- capture한 MCP 이름 중 `catalog/mcp.json`에 있는 것만 opt-in으로 고른다. 카탈로그에 없는 이름은 버전이 고정되지 않아 건너뛰고 보고한다.
- user 범위에는 플러그인 설치(`--plugin`, 64), 도구 설치, MCP 핸드셰이크, 감사가 없다. Claude 플러그인은 capture한 `~/.claude/settings.json` 키(`/enabledPlugins/<id>` 등)로만 켠다.
- 키트가 쓰려는 경로에 내용이 다른 파일이 이미 있으면(예: OMX를 직접 설치한 PC) CONFLICT이고 덮어쓰지 않는다. 같은 내용이면 키트 소유로 인수하지 않는다(uninstall이 지우지 않음).
- `CODEX_HOME`, `CLAUDE_CONFIG_DIR`은 home 안일 때만 따른다. 밖이면 65다.

### 2.4 Action

모든 Action은 `agent`, `scope`, `path`, `owner`, `network: bool`, `risk: low|medium|high`, `reason`을 갖는다.

| Action | 쓰는 곳 | 소유 기록(§3.1) |
|---|---|---|
| `CreateFile` / `UpdateFile` | 스킬 파일, OMX 파일 | `files[]` |
| `UpdateManagedBlock` | AGENTS.md, CLAUDE.md, config.toml | `blocks[]` |
| `MergeJsonKeys` | `.mcp.json`, settings.json | `json_keys[]` |
| `CopyTree` | 스킬 폴더. 여러 `CreateFile`로 펼친다 | `files[]` |
| `RemoveOwned` | uninstall | 해당 기록 삭제 |
| `InstallTool` | 기존 tools 동작. 새 경로에서는 `network: true`로 두고 D-14 확인을 받는다 | 없음 |
| `ManualStep` | 사용자가 직접 실행할 명령: Claude user MCP, OMX 자체 설치, 플러그인 `/plugin` | 없음. 보고서에 출력 |

결과 판정은 기존 `Outcome` 어휘(`kit/model.py`)를 그대로 쓴다. 기존 `FileChange`(`kit/plan.py:14-21`)는 `CreateFile`·`UpdateManagedBlock`의 계획 결과 표현으로 재사용한다.

### 2.5 공통 실행기

1. **preflight:** 대상 경로를 확인하고, 키트 자신을 대상으로 지정하면 거부한다(65). 쓰기 위치는 기존 `safe_path`로 검사하고, user scope에서는 `home` 아래만 허용한다.
2. **확인:** `network: true` 또는 `scope=user`인 Action이 있으면 확인을 받는다(D-14, ADR-018). TTY면 묻고, 아니면 `--yes`가 필요하다.
3. **백업:** 바뀔 파일을 `.kit/backups/<stamp>/` 또는 `~/.kit-backups/<stamp>/`에 복사한다.
4. **쓰기:** writer별로 변환한 뒤 `.kit-tmp`에 쓰고 rename한다(기존 `kit/register.py:32-40`).
5. **매니페스트 갱신:** 중간에 실패하면 이번 실행에서 쓴 파일을 백업으로 되돌리고, 매니페스트는 갱신하지 않는다.

### 2.6 새 에이전트 추가 절차

P7에서 `docs/v2/EXTENDING.md`로 문서화한다. 절차는 다음과 같다.
1. Adapter 클래스를 만든다.
2. `registry.py`에 등록한다.
3. 표 2.3에 열을 추가한다.
4. `catalog/*.json`의 `agents`에 값을 추가한다.
5. 골든·adapters 테스트를 추가한다.

## 3. 데이터 모델 (P2-T4)

모든 파일은 JSON(`json` 표준 모듈)이고 최상위에 정수 `"schema"`를 둔다. 알 수 없는 상위 schema는 오류(65)이고, 알 수 없는 필드는 보존한다.

### 3.1 설치 매니페스트

project 범위는 `.kit/state/install-manifest.json`, user 범위는 `~/.kit-state/manifest.json`이다. 두 파일의 형식은 같다.

```json
{
  "schema": 1,
  "kit_version": "2.0.0",
  "scope": "project",
  "installs": [
    {
      "agent": "claude",
      "profiles": ["core", "hitl"],
      "policy": "standard",
      "installed_at": "2026-11-05T10:12:00+09:00",
      "files":     [{"path": ".claude/skills/tdd-automator/SKILL.md", "sha256": "…"}],
      "blocks":    [{"path": "CLAUDE.md", "marker": "hackathon-kit", "sha256": "…"}],
      "json_keys": [{"path": ".mcp.json", "pointer": "/mcpServers/sequential-thinking", "sha256": "…"},
                    {"path": ".claude/settings.json", "pointer": "/permissions/allow", "element_sha256": "…"}],
      "manual_steps": ["claude mcp add --scope user …"],
      "backups":   [".kit/backups/20261105-101200/"],
      "opt_in":    {"mcp": ["playwright"], "plugins": ["security-guidance"]}
    }
  ]
}
```

- 원문과 다른 점:
  - `marker`는 `hackathon-kit`이다(ADR-003).
  - 최상위 `scope`를 추가했다.
  - 배열 원소 소유를 위한 `element_sha256`(ADR-005)과 `manual_steps`를 추가했다.
- user 범위의 `path`는 **home 기준 상대 경로**(`.codex/AGENTS.md`)로 저장한다. `~/` 접두어는 붙이지 않는다(P4-T7: 기존 safe_path·백업 코드를 그대로 쓰기 위해서다. 의미는 같다). 상태·백업·로그는 `~/.kit-state/`, `~/.kit-backups/`, `~/.kit-state/logs/`다.
- **인수(adoption):** v1 `.kit/state.json`의 `files {rel: sha256}`를 읽는다. 현재 해시가 v1 기록이나 키트가 배포한 알려진 내용과 같으면 키트 소유로 인정하고, 다르면 `CONFLICT`다. v1 파일은 남겨 둔다(ADR-006).

### 3.2 프로필 v2

원문 §7.4의 스키마와 규칙을 따르되, 다음을 조정한다.
- 스킬 참조는 **카탈로그 이름**(§3.6)으로 한다. 실제 위치는 카탈로그가 정한다.
- `algorithm-decision-reviewer` 대신 `algorithm-options`의 standard overlay를 쓴다(Q7). 원문 표의 core "기존 8개 스킬"은 11개로 읽는다(Q1).
- 새 경로의 기본값은 `--profile core,hitl`이다(ADR-008).
- 기존 v1 파일 5개는 읽을 때 정규화한다.
  - `extends: "x"` → `["x"]`
  - `skills`·`mcp` 리스트 → `{"shared": […]}`
  - `agents` 기본값은 등록된 모든 에이전트(`["claude", "codex"]`)다. (P3-T5 정정: 처음 설계의 `["codex"]`로 하면 `--agent claude`로 `core`를 설치할 때 스킬이 모두 빠진다.)
  - `policy`는 `null`
- 팩(`profiles/packs/*.json`)은 같은 스키마를 쓰고 `"kind": "pack"`을 둔다. 팩은 `extends`를 쓸 수 없다.
- P4-T6 신규 프로필(v2 파일, `profiles/`):

  | 프로필 | 구성 | 해석 순서 |
  |---|---|---|
  | `fullstack` | `extends: [python, web]`, `packs: [hitl]`. standard에서는 카탈로그의 `web`·`fullstack` 팩 스킬(디자인 3개)이 붙는다 | core → python → web → hitl → fullstack |
  | `ai-research` | `extends: [data]`, `packs: [hitl]`, 필수 스킬에 `benchmark`·`algorithm-options` 추가. U-40 후보는 승인 대기(07 §3.3) | core → python → data → hitl → ai-research |
  | `hackathon` | `extends: [core]`, `packs: [hitl]`, 필수 스킬에 `benchmark` 추가, `recommended_policy: restricted` | core → hitl → hackathon |

- `recommended_policy`(v2 선택 키): 정책을 강제하지 않는다(ADR-015). 해석된 정책과 다르면 보고서 머리에 `Warning:` 줄, JSON에 `policy_warnings`를 낸다.
- 기존 경로는 v1 파일만 프로필로 본다(`kit.profiles.available_profiles`가 `"schema"` 키가 있는 파일을 뺀다). 그래서 기존 경로의 `--profile` 선택지와 오류 문구는 바뀌지 않고, `--profile fullstack`은 64다.
- 정책 렌더링(ADR-004, P4-T6): standard = `core.md`(제목, 10개 원칙, 스킬 위치) + `light-path.md`(L/S/C 등급) + `skills.md`(언제 어떤 스킬을 쓰는지, P5-T1) + `testing.md` + `hitl.md` + `environments/standard.md`(허용·사전 승인). 원칙 문장은 모듈 한 곳에만 있고 `{agent}`, `{skill_root}`만 에이전트별로 바뀐다. restricted = 루트 `AGENTS.md` 바이트 그대로(에이전트 공통). 그래서 `environments/restricted.md`는 만들지 않았다(같은 원문을 두 곳에 두지 않기 위해).

### 3.3 Task 상태 `.kit/work/tasks.json`

- 원문 형식을 그대로 쓴다.
- `approvals[].by`는 `human-cli | human-hook | agent-recorded` 중 하나다.
- ADR-011에 따라 Codex에서도 `human-hook`이 기록될 수 있다. 그때는 보고서에 "Codex 훅: 보조 수단" 주석을 붙인다.
- **P5-T2 구현(`kit/tasks.py`, `kit/task_cli.py`).** 원문 형식에 다음 필드를 더한다.
  - 각 Task: `grade`(L/S/C), `requirements`, `subtasks[]`(`id`는 `<Task>.<n>`, `state` TODO/DONE), `report`(작업 공간 기준 상대 경로), `submitted_sha256`(submit 때 보고서 해시), `approval`(마지막 승인 기록), `history[]`(`at`, `event`, `detail`).
  - `approvals[]`: `task`, `at`, `by`, `evidence`(최대 2000자, 마스킹), `report_sha256`.
  - 상태: TODO → IN_PROGRESS → SUBMITTED → APPROVED, SUBMITTED → CHANGES_REQUESTED → IN_PROGRESS. 동시에 IN_PROGRESS는 하나만.
  - 읽을 때 검사한다: schema 1, 중복 id, 알 수 없는 상태, 없는 선행 Task, 의존 순환, 형식이 틀린 승인 기록 → 65. 저장은 임시 파일 뒤 `os.replace`.
  - submit 검사: 보고서 §5.6의 1~9절이 모두 있음, must 요구사항마다 테스트 표 행이 있음, `NOT RUN`은 `NOT RUN: <이유>`. must 판정은 `trace.json`이 있으면 그 `priority`, 없으면 Task의 요구사항 전부(검토자 결정 2026-11-07).
  - approve는 SUBMITTED에서만, 보고서가 submit 뒤 바뀌지 않았을 때만 된다. 승인 뒤 보고서가 바뀌거나 없어지면 `task status`가 경고하고 1을 낸다.
  - **정직성 한계.** L1은 기록과 탐지다. 에이전트가 `--by agent-recorded`로 사용자 발화를 지어내거나 `tasks.json`을 직접 고치는 것을 막지 못한다. 그래서 `by`를 모든 출력에 드러내고, 막는 장치는 L2 훅(P5-T2b)으로 나눴다(검토자 결정 2026-11-07).

### 3.4 요구사항·추적 `.kit/work/trace.json`

- 원문 형식을 그대로 쓴다.
- 테스트 상태는 저장하지 않고, JUnit XML과 합칠 때 계산한다.
- JUnit XML에 없는 locator는 `NOT RUN`으로 표시한다(ADR-012).

### 3.5 반례 `.kit/work/counterexamples.json`

- 형식은 `{"schema": 1, "items": [ … ]}`이다.
- 각 항목은 원문 §10.5.3 형식이고, `status`에 `NEEDS_SPEC`이 포함된다.
- 확장된 `counterexample-hunter`의 standard overlay가 이 형식으로 기록하도록 지시한다(Q7).

### 3.6 스킬 카탈로그 `catalog/skills.json` (신규)

```json
{
  "schema": 1,
  "skills": [
    {"name": "tdd-automator", "location": ".agents/skills/tdd-automator", "origin": "kit",
     "agents": ["codex", "claude"], "packs": ["core"], "policies": ["restricted", "standard"]},
    {"name": "counterexample-hunter", "location": ".agents/skills/counterexample-hunter",
     "overlay": "shared/skills/overlays/counterexample-hunter", "overlay_policies": ["standard"],
     "agents": ["codex", "claude"], "packs": ["core"], "policies": ["restricted", "standard"]},
    {"name": "launch-compliance-check", "location": "shared/skills/launch-compliance-check", "origin": "kit",
     "agents": ["codex", "claude"], "packs": ["launch"], "policies": ["standard"]},
    {"name": "example-external", "location": "third_party/<owner>-<repo>/skills/<name>",
     "origin": "source:<sources.lock.json id>", "agents": ["codex", "claude"],
     "packs": ["web"], "policies": ["standard"], "replaces": ["<기존 스킬 이름>"]}
  ]
}
```

- 외부 항목은 P4-T3 평가 뒤에 채운다.
- `origin`은 `kit` 또는 `source:<id>`다.
- `replaces`에는 D-20의 `replace-in-standard` 결정을 기록하고, standard 경로에서만 적용한다.
- **불변 조건:** `policies`에 `restricted`가 있는 항목은 `.agents/skills/`의 기존 11개뿐이다(V-22).
- **P4-T4에서 추가한 필드와 규칙**(`kit/catalog.py`, `kit/commands.py::_catalog_skills`):
  - `include: {"<스킬 안 경로>": "<키트 파일>"}`: 기본 층에 파일 하나를 더한다(예: 업스트림 LICENSE, 원문 사본). 기본 층 파일과 경로가 겹치면 오류다.
  - `requires`: 함께 설치돼야 하는 스킬. 링크나 스크립트가 `../<스킬>/`을 가리키는 경우다(superpowers 계획 체인). 검사기는 이 스킬의 파일을 가리키는 링크만 허용하고, 계획에 없으면 BLOCKED다.
  - `replaces`: 이 항목이 쓰이는 정책에서, 프로필에 있지만 쓸 수 없는 스킬을 같은 자리·같은 필수 여부로 대신한다. 출력에 `replaced skills: A -> B`로 보인다.
  - `packs`: 고른 프로필·팩 이름 중 하나가 있으면, 에이전트·정책에 맞는 스킬이 목록에 더해진다(v1 `core`를 고치지 않고 standard에 스킬을 더하는 방법).
  - 같은 이름은 정책이 겹치지 않을 때만 두 번 쓸 수 있다(`systematic-debugging`: restricted는 키트판, standard는 superpowers판).
  - `third_party/`에서 오는 파일은 설치 전마다 lock 해시와 비교한다. 다르면 BLOCKED이고 아무것도 쓰지 않는다.
- `catalog/mcp.json`과 `catalog/plugins.json`은 원문 P4-T5 필드(`enabled_by_default`, `disabled_reason`, `network_egress`, `file_access`)에 `agents`별 매핑을 더한 형식이다. 기존 `mcp/manifest.json`·`allowlist.json`은 기존 경로가 계속 읽는다.
- **P4-T5 확정**(`kit/mcp_catalog.py`). 카탈로그가 규칙을 어기면 BLOCKED이고 아무것도 쓰지 않는다.
  - 공통 필수: `transport, agents, policies, risk, enabled_by_default, disabled_reason, network_egress, file_access`. 기본으로 꺼진 항목은 `disabled_reason`이 있어야 하고, 켜진 항목은 `null`이다. `risk: high`는 기본으로 켤 수 없다.
  - MCP: `transport`는 `stdio`만 받는다. `url`·`headers`·`bearer_token_env_var`·`type` 키는 거부한다. `command`가 있는 항목만 설치할 수 있고, 명령은 `mcp/allowlist.json`의 `commands`(npx, uvx) 안이어야 한다. `version`은 정확한 버전이어야 하고(`latest`, `^`, `~`, 범위 거부) `args`에 `package@version`(uvx는 `package==version`)이 그대로 있어야 한다. `command`가 없는 항목은 목록 전용이고 기본으로 켤 수 없다. `source`가 있으면 lock의 `kind: mcp` 항목과 버전이 같아야 한다. 비밀처럼 보이는 `env` 이름은 `risk: high`에서만 받는다.
  - 플러그인: `source`는 전체 `https://` URL과 40자 `sha`로 고정한다. Claude는 `github`·`url`·`git-subdir`, Codex는 `url`·`git-subdir`만 받는다(Codex marketplace 형식에 `github`가 없음). lock 항목(`kind: plugin`, id는 플러그인 이름 또는 선택 키 `lock`)이 있어야 하며 `commit`이 `sha`와 같아야 한다. 선택 키 `category`는 Codex marketplace 항목에 들어간다. 처음 02 매트릭스에서는 Codex 고정 방법을 찾지 못해 거부했으나, codex-cli 0.166.0에서 `sha` 고정 설치를 확인해 2026-11-06 지원으로 바꿨다(사용자 선택 "2번").
  - 선택: 프로필의 `mcp` 목록 중 기본으로 켜진 것은 들어가고, 꺼진 것은 `off by default; add --mcp NAME`으로 건너뛴다. `--mcp`·`--plugin`으로 고른 것은 에이전트·정책에 맞으면 들어간다. 건너뛴 이유는 plan·보고서·JSON에 모두 나온다(`skipped_mcp`, `skipped_plugins`).
  - 고른 서버는 `mcpconfig.McpSelection`(이름 목록 + 카탈로그 항목)으로 기존 렌더러(`.codex/config.toml` 블록, `.mcp.json` 키)와 MCP 점검에 그대로 넘어간다. 기존 경로는 계속 `mcp/manifest.json`을 읽는다(골든 테스트).
  - 새 경로의 보안 감사는 `mcp/allowlist.json`의 금지 키·환경 변수·명령 규칙에, 서버 목록만 카탈로그의 설치 가능 서버로 바꿔 쓴다. 예외는 P4-T9의 `declared_env` 하나다.
  - Claude 플러그인 선언: `.claude/settings.json`의 키트 소유 키 두 개. `/extraKnownMarketplaces/hackathon-kit` = `{"source": {"source": "settings", "name": "hackathon-kit", "plugins": [{name, source}]}}`, `/enabledPlugins/<plugin>@hackathon-kit` = `true`. 소유·삭제 규칙은 `.mcp.json`과 같다(ADR-005). 제거 후 비어 버린 상위 객체는 지우고, 문서가 `{}`가 되면 파일을 지운다. 이 선언은 저장소를 받는 팀원용이다(폴더 신뢰 후 `/plugin install`).
  - Claude 플러그인 설치(`kit/plugin_install.py`, Claude Code 2.1.319로 격리된 `CLAUDE_CONFIG_DIR`에서 확인): 셸 CLI는 프로젝트 설정에만 선언된 marketplace를 등록하지 않는다(세션 안에서 신뢰 후 등록). 그래서 키트는 같은 카탈로그를 `.kit/claude-marketplace/.claude-plugin/marketplace.json`(키트 소유 파일)으로 쓰고, 네트워크 허용 시 `claude plugin marketplace add <그 폴더> --scope local` → `claude plugin install <id> --scope project`를 실행한다. `--scope project`로 marketplace를 더하면 공유 `settings.json`에 절대 경로가 들어가므로 쓰지 않는다. 실행 결과는 매니페스트 `plugin_installs`에 남고, `verify`는 `claude plugin list --json`으로, `uninstall`은 `claude plugin uninstall` → `marketplace remove --scope local` 후 파일을 지운다. 키트 때문에 생긴 `settings.local.json`이 빈 객체만 남으면 지운다. 플러그인 source URL은 전체 `https://` URL이어야 한다(`owner/repo` 축약은 clone 실패).
  - Codex 플러그인 설치(같은 모듈, codex-cli 0.166.0으로 격리된 `CODEX_HOME`에서 확인): 키트는 `.agents/plugins/marketplace.json`(키트 소유 파일, 항목마다 `policy: {installation: AVAILABLE, authentication: ON_INSTALL}`)을 쓴다. `codex plugin`은 이 파일을 스스로 읽지 않으므로(폴더 신뢰·git 저장소 모두 시험) 네트워크 허용 시 `codex plugin marketplace add <작업 폴더>` → `codex plugin add <id>`를 실행한다. Codex에는 설치 범위 옵션이 없어 `~/.codex/config.toml`에 `[marketplaces.hackathon-kit]`와 `[plugins."<id>"] enabled = true`가 들어가고, 플러그인은 **모든 프로젝트에서 켜진다**. 네트워크 요구 문구와 매니페스트 기록(`scope: user`)이 이를 밝힌다. `verify`는 `codex plugin list --json`의 `installed` 목록으로, `uninstall`은 `codex plugin remove` → `codex plugin marketplace remove`로 되돌린다. Windows에서 `CODEX_HOME` 경로가 매우 길면 clone이 260자 경로 한도로 실패했다.

- **P4-T9 API 키 안내**(`kit/credentials.py`, 검토자 요청 2026-11-06). 키가 필요한 MCP 서버·플러그인·스킬은 카탈로그 항목에 선택 키 `credentials`를 둔다.
  ```json
  "credentials": [{"env": "ANTHROPIC_API_KEY", "required": false,
                   "purpose": "…", "get_it": "https://platform.claude.com/settings/keys", "cost": "pay per use"}]
  ```
  - 필드: `env`(대문자 `UPPER_SNAKE`), `required`(true/false), `purpose`, `get_it`(`https://` 페이지), 선택 `cost`. 다른 필드는 거부한다(값을 넣을 자리를 만들지 않음). 어기면 BLOCKED다.
  - 키가 필요한 서버·플러그인은 기본으로 켤 수 없다. 키가 필요한 스킬은 기본 팩(`core`, `hitl`)에 넣을 수 없다(검토자 결정 "기본 비활성 유지").
  - 설정 파일에는 참조만 쓴다. Codex는 `env_vars = ["NAME"]`(셸에서 그대로 넘김), Claude `.mcp.json`은 `"env": {"NAME": "${NAME}"}`, Claude user 범위 수동 명령은 `claude mcp add … -e 'NAME=${NAME}'`이다(작은따옴표라 셸이 펼치지 않음). 키 값은 묻지도, 읽어 보여 주지도, 쓰지도 않는다.
  - 감사: 새 경로 허용 목록(`mcp_catalog.allowlist`)에 `declared_env = {서버: [이름]}`을 더한다. 그 서버가 선언한 이름이 **참조로만** 있으면(`env_vars` 원소, 또는 값이 정확히 `${NAME}`) 비밀형 이름 규칙의 예외다. 값이 쓰였거나, 다른 이름을 참조하거나, 선언하지 않았거나, 다른 서버가 선언한 이름이면 그대로 FAIL이다. 기존 경로 허용 목록에는 예외가 없다.
  - 설정 여부는 키트 프로세스의 환경 변수 이름으로만 본다(값이 비어 있지 않으면 `set`). 필수 키가 없어도 종료 코드는 그대로이고 `Next action`에 한 줄이 생긴다.
  - 실제 항목: `security-guidance` 플러그인의 `ANTHROPIC_API_KEY`(선택). 고정한 커밋의 README에 따르면 키가 없으면 Claude Code 로그인(`/login`)을 쓰고, 그것도 없으면 패턴 경고만 실행한다. MCP `context7`(`@upstash/context7-mcp@4.5.1`, MIT, 기본 꺼짐, 검토자 승인 2026-11-06)의 `CONTEXT7_API_KEY`(선택).
  - **실제 CLI 확인(2026-11-06, codex-cli 0.166.0, Claude Code 2.1.319, 격리한 `CODEX_HOME`/`CLAUDE_CONFIG_DIR`, 가짜 값, 시험용 stdio 서버).** 세 형식 모두 값이 있으면 서버가 실제 값을 받았다. Codex `env_vars`는 값이 없으면 변수를 넘기지 않는다(그 줄이 없으면 값이 있어도 넘기지 않음). Claude `.mcp.json`의 `${NAME}`과 `claude mcp add -e 'NAME=${NAME}'`(user 설정에 글자 그대로 저장되고 시작할 때 펼침)는 값이 없으면 **`${NAME}` 글자를 그대로** 넘기고 `claude mcp list`에 경고를 낸다(Claude 문서와 같음). 서버가 그 글자를 키로 오해할 수 있으므로 키트 안내는 키를 설정하고 새 터미널에서 에이전트를 다시 켜라고 한다. `context7` 4.5.1은 이 글자를 키로 쓰지 않고 무시한다(소스 확인). 프로젝트 `.mcp.json` 서버는 Claude가 처음에 승인을 받아야 시작한다.
- **수동 안내 카탈로그 `catalog/manual.json`(U-23, 검토자 결정 2026-11-06).** 키트가 실행·설치하지 않고 설명만 하는 도구. 필수 필드 `agents, policies, risk, license, summary, network_egress, file_access, steps(문자열 목록), undo(문자열 목록), docs(https)`, 선택 `version, package, origin, commit, credentials`. 첫 항목은 `claude-code-router` 3.1.3(Claude 전용, standard, high). 단계는 README와 공식 문서(ccrdesk.top)에서 가져왔고 CLI로 실행해 보지는 않았다.

### 3.7 외부 리소스 잠금 `sources.lock.json`

원문 P4-T4 스키마를 기준으로 하고, ADR-021 스펙 §6의 필드를 다음처럼 맞춘다.

| 스펙 §6 필드 | 확정 필드 |
|---|---|
| `repo` | `origin` |
| `mode: vendored` | `integration: vendored-verbatim`. 수정했으면 `adapted` |
| `mode: reference` | `integration: referenced` |
| `files {path: sha256}` | **추가 필드로 유지**. `content_sha256`은 정렬한 `path\0sha256\n` 목록의 sha256 |
| `ref`, `added`, `added_by`, `packs`, `overlap` | 추가 필드로 유지 |

```json
{
  "schema": 1,
  "sources": [
    {
      "id": "oh-my-codex",
      "kind": "skill-bundle",
      "origin": "https://github.com/Yeachan-Heo/oh-my-codex",
      "path": "skills/",
      "ref": "main",
      "commit": "<40자 SHA>",
      "version": null,
      "license": "MIT",
      "license_file": "third_party/Yeachan-Heo-oh-my-codex/LICENSE",
      "integration": "vendored-verbatim",
      "local_paths": ["third_party/Yeachan-Heo-oh-my-codex/"],
      "files": {"skills/<name>/SKILL.md": "<sha256>"},
      "content_sha256": "…",
      "agents": ["codex"],
      "scope": ["user"],
      "packs": [],
      "risk": "medium",
      "added": "2026-11-05",
      "added_by": "P4-T3",
      "overlap": [],
      "verification": {"status": "unverified", "by": null, "at": null, "notes": ""}
    }
  ]
}
```

- `kind`는 `skill | skill-bundle | mcp | plugin | reference` 중 하나다.
- `added_by`는 `P4-T3 | source add | migrated` 중 하나다(`migrated`는 v1 NOTICES에서 옮긴 항목).
- **P4-T4 확정:** `files`의 키는 **키트 루트 기준 경로**다(`third_party/...`, 옮겨 온 항목은 `.agents/skills/...`). `license_file`은 그 항목의 `files` 안에 있어야 한다. `referenced` 항목은 `files`가 비어 있어야 한다. `commit`은 40자 SHA만 받는다.
- `third_party/**`는 `.gitattributes`에서 `-text`라서 git이 줄 끝을 바꾸지 않는다(해시 보존).
- 기존 `THIRD_PARTY_NOTICES.md`의 항목은 내용을 유지한 채 이 파일로 옮긴다.
- 오프라인 검증 명령 이름은 `source check`다(05_CLI_SPEC). P4-T4는 라이브러리 `kit/sources.py::check`와 테스트까지 만들고, CLI 연결은 `kit source` 전체와 함께 P4-T8에서 한다.
- **P4-T8에서 `kit source add`가 쓰는 lock 필드:**
  - `paths`: `--path` 목록. 같은 주소인지 판정하고 `update`할 때 다시 쓴다.
  - `added_by: "source add"`: `update`와 `remove`는 이 값이 있는 항목만 다룬다.
  - `overlap[]`: `{skill, with, score, decision}`. decision은 `replace-in-standard`, `keep-both`, 또는 null이다.
- **vendored 위치:** `third_party/<owner>-<repo>/<저장소 안 경로>`. 카탈로그 항목은 `policies: ["standard"]`, `origin: "source:<id>"`로 만든다. 라이선스 파일이 스킬 폴더 밖(저장소 루트)에 있으면 `include: {"LICENSE": …}`로 스킬 옆에 함께 설치한다.
- **`--replaces X`(D-20 replace-in-standard):**
  - 기존 `replaces`는 X를 그 정책에서 쓸 수 없을 때만 대신하므로, 새 항목에 `replaces: [X]`를 두는 것만으로는 부족하다. 그래서 X의 카탈로그 항목에서 `standard`도 뺀다.
  - restricted 정책과 `.agents/skills` 미러는 바뀌지 않는다(V-22 테스트).
  - `remove`하면 X에 `standard`를 되돌린다.
- `NOTICES` 구간은 `<!-- kit-source:begin <id> -->` … `<!-- kit-source:end <id> -->`로 감싸서 `update`·`remove`가 그 구간만 고친다.
- `docs/v2/07_SOURCES_EVALUATION.md`가 있으면 `## 9. \`kit source\` 기록` 표에 add·update·remove를 한 줄씩 덧붙인다.

### 3.8 capture 허용 목록 `user/capture-allowlist.json` (신규, ADR-019)

P4-T7에서 만든 실제 파일은 `user/capture-allowlist.json`이다. 아래는 설계 당시의 예시다.

```json
{
  "schema": 1,
  "codex": {
    "files": [{"from": "~/.codex/AGENTS.md", "to": "user/codex/AGENTS.block.md",
               "mode": "sections", "sections_exclude": ["<머신 전용 섹션 제목>"]}],
    "toml_tables": ["mcp_servers.context7", "mcp_servers.playwright", "plugins"],
    "skills_dirs": ["~/.codex/skills/*"],
    "skills_exclude": [".system", "superpowers"]
  },
  "claude": {
    "files": [{"from": "~/.claude/CLAUDE.md", "to": "user/claude/CLAUDE.block.md", "mode": "whole"}],
    "json_pointers": [{"from": "~/.claude/settings.json",
                       "pointers": ["/enabledPlugins", "/extraKnownMarketplaces", "/attribution", "/model"]}],
    "mcp_from_claude_json": {"names": ["playwright", "context7"], "values": "names-and-commands-only"}
  },
  "always_redact": {"env_values": true, "header_values": true, "home_path": "${HOME}"}
}
```

- 여기에 없는 키와 파일은 가져오지 않는다. 다음 항목은 목록에 없으므로 들어오지 않는다.
  - `projects.*`, auth, 세션, sqlite
  - `superpowers`: symlink이므로 외부 소스로 다룬다
  - `.system`: Codex 번들
- 마지막 단계에서 `kit/secrets_scan.py`가 결과 전체를 검사한다. 하나라도 걸리면 아무것도 쓰지 않고 1로 끝난다.
- 예시의 키 이름은 global-inventory에서 확인한 것이다. 최종 목록은 P4-T7에서 승인을 받는다.
- **P4-T7 구현과 예시의 차이:**
  - Codex 표는 `features`, `plugins.*`만 가져온다. computer-use 플러그인 2개는 뺀다(PC 전용).
  - `mcp_servers.*`는 값(명령·경로·env)을 가져오지 않고 **이름만** `user/codex/mcp.json`에 남긴다. 설치할 때는 카탈로그 항목(버전 고정)을 쓴다.
  - Claude MCP도 `~/.claude.json`(또는 `CLAUDE_CONFIG_DIR/.claude.json`)에서 이름과 전송 방식만 읽는다.
  - 스킬·prompts·agents는 복사하지 않고 `inventory.json`에 이름과 출처 판정만 남긴다(omx 태그와 같음 / 다름 / 링크 / omx setup 생성 / 모름).
  - 최상위 키(`model`, `developer_instructions` 등)는 가져오지 않고 이름만 보고한다.
  - 정책 파일은 키트 구간을 먼저 지우고, 2단계 제목(`## `) 단위로 나누며 코드 펜스 안은 제목으로 보지 않는다.
  - 비밀값 스캔은 `secrets_scan.find`에 bearer 토큰과 `*TOKEN|SECRET|PASSWORD|API_KEY = "리터럴"` 패턴을 더한다. `${ENV:…}`, `${HOME}`, 함수 호출은 걸리지 않는다.

### 3.9 schema 버전 정책

- 하위 호환이 되는 필드 추가는 같은 schema 번호를 유지한다.
- 의미가 바뀌면 schema 번호를 올리고, 읽는 쪽이 이전 버전을 정규화한다.
- 형식마다 예시 파일을 `tests/fixtures/schemas/`에 두고 왕복 테스트(읽기 → 쓰기 → 동일)를 한다.
