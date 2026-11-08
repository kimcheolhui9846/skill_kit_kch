# Codex에서 쓰기

설치 공통 절차는 `INSTALL.md`에 있다. 여기에는 Codex에만 해당하는 내용을 적는다. 에이전트 안 명령(`/skills` 등)은 공식 문서에서 확인한 것만 적었다(`docs/v2/AGENT_LOAD_CHECK.md`의 출처, 2026-11-08).

## 1. 설치되는 것 (project 범위)

```bash
kit install --agent codex
kit install --agent codex --policy restricted     # 시험용: v1과 같은 스킬 11개
kit install --agent codex --mcp context7 --hooks  # MCP와 승인 훅을 함께
```

| 파일 | 내용 | 키트가 쓰는 범위 |
|---|---|---|
| `AGENTS.md` | 작업 정책 | `<!-- hackathon-kit:begin -->` … `end` 구간만 |
| `.agents/skills/<이름>/` | 스킬(기본 17개, restricted 11개) | 키트가 만든 파일만 |
| `.codex/config.toml` | MCP 서버(프로필이나 `--mcp`로 고른 것) | `# hackathon-kit:begin` … `end` 구간만 |
| `.codex/hooks.json`, `.codex/hooks/kit_approval.py` | 승인 훅(`--hooks`만) | 키트 소유 키만 |

- 기본 프로필(`core,hitl`, standard)은 MCP를 등록하지 않는다. `python`·`web` 계열 프로필은 `sequential-thinking`을 등록한다. 서버 목록과 위험도는 `docs/CATALOG.md`에 있다.
- 설정 파일에는 API 키 값을 쓰지 않는다. `env_vars = ["CONTEXT7_API_KEY"]`처럼 환경 변수 이름만 둔다.

## 2. 신뢰 설정

Codex는 프로젝트의 `.codex/` 층(`config.toml`의 MCP, `hooks.json`)을 **신뢰한 프로젝트에서만** 읽는다(공식 문서 CX-MCP, CX-HK).

- `AGENTS.md`와 `.agents/skills/`는 신뢰와 관계없이 읽힌다.
- 작업 공간에서 Codex를 처음 열 때 신뢰 확인이 나오면 신뢰를 고른다. 이 기록은 Codex가 `~/.codex/config.toml`에 남긴다. 키트가 쓰는 것이 아니다.
- 신뢰 전에는 키트 보고서의 MCP 항목이 `UNVERIFIED`다. 실패가 아니다.
- 승인 훅은 신뢰한 뒤에도 Codex의 `/hooks`에서 검토하고 신뢰해야 실행된다. 새 훅이나 바뀐 훅은 그때까지 건너뛴다.

## 3. 로드 확인

| 확인 | 어디서 | 명령 |
|---|---|---|
| 지침 | 셸, 작업 공간 | `codex --ask-for-approval never "Summarize the current instructions."` |
| 스킬 | Codex TUI | `/skills`, 또는 입력창에 `$` |
| MCP | Codex TUI / 셸 | `/mcp` / `codex mcp list` |
| 훅 | Codex TUI | `/hooks` |

- 이 명령들은 에이전트 안에서만 결과를 볼 수 있다. 이번 문서 작업에서는 실행하지 않았다(**미검증**).
- 검토자가 실행하고 결과를 적는 표가 `docs/v2/AGENT_LOAD_CHECK.md` 1절이다.
- 키트의 `verify`는 파일 상태만 확인한다. 그래서 `Load UNVERIFIED (run /skills in Codex)`로 나온다.

## 4. 사용자 범위

```bash
kit install --agent codex --scope user --dry-run
```

- `~/.codex/AGENTS.md`(키트 구간), `~/.codex/skills/`, `~/.codex/config.toml`(키트 구간), OMX 스킬과 prompts가 대상이다.
- `~/.codex/skills`는 Codex 공식 문서에 없는 경로다. 공식 사용자 경로는 `$HOME/.agents/skills`다. 2026-11-05 검토자가 Codex 0.166.0의 `/skills`에서 보이는 것을 확인했다. 문서화되지 않은 호환 동작이므로 Codex를 업데이트하면 다시 확인한다(`docs/v2/02_COMPATIBILITY_MATRIX.md`).
- `~/.codex/AGENTS.md`가 28 KiB를 넘을 것 같으면 계획에 경고가 나온다.

## 5. 제약

- **훅은 보조 수단이다.** Codex 훅은 "guardrail, not a complete enforcement boundary"(공식 문서)다. 셸로 우회할 수 있다. 키트의 상태 기계(L1)가 두 번째 방어선이다(`docs/SECURITY.md`).
- **Codex 플러그인:** 카탈로그에 Codex 플러그인은 없다. Codex에는 플러그인 설치 범위가 없어서 설치하면 모든 프로젝트에서 켜진다(`catalog/plugins.json`의 설명).
- **`both` 설치에서 `.claude/skills`가 Codex에 보이는지:** 공식 문서에 근거가 없다. `/skills`로 직접 확인한다(점검표 C-02).
- **시험 환경:** 시험 중에는 운영 환경이 허용한 Codex만 쓴다. 키트는 파일을 배치할 뿐 외부 모델이나 네트워크를 부르지 않는다(`--offline`). 시험 규칙에 맞추려면 `--policy restricted`를 쓴다.
