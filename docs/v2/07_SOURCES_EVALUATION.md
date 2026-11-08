# 07 외부 리소스 평가 보고서 (P4-T3, §14 프로토콜)

- 작성일: 2026-11-06. **상태: 2026-11-06 검토자 승인.** 채택안 A1~A5·R1 승인, Q1~Q4 결정은 §8. 승인 범위 밖의 외부 파일은 넣지 않는다.
- 대상: 사용자 목록 U-01~U-49(`08_USER_SOURCES.md`), OMX(U-51), §14.1 후보 5개, 이 PC의 전역 항목(REQ-SRC-008).
  U-50 `launch-compliance-check`는 키트가 직접 쓰는 스킬이라 외부 리소스가 아니다(P5).
- 관련 요구사항: REQ-SRC-001/004/005/007/008, 원문 §14.3, R-07.

## 0. 확인 방법과 확인 수준

| 무엇을 | 어떻게 (2026-11-06 실행) | 결과 위치 |
|---|---|---|
| 저장소·기본 브랜치 HEAD 커밋·보관 여부·별·열린 이슈·최근 릴리스 | `gh api repos/<r>`, `commits/<branch>`, `releases/latest` | `docs/v2/evidence/p4t3-github-probe.json` |
| 라이선스 | `gh api repos/<r>/license`로 **LICENSE 원문 첫 부분을 읽음**. 루트에 없으면 README의 License 절과 스킬 폴더의 `LICENSE.txt`·frontmatter `license:`를 직접 읽음 | 아래 표 4열 |
| npm 수명주기 스크립트 | 루트 `package.json`의 `preinstall/install/postinstall/prepare` | 아래 표 6열 |
| 스킬 파일·스크립트·훅 | 고정 커밋의 git tree를 읽고 `.md/.sh/.py/.js/.mjs` 본문에서 원격 호출, 파이프 셸, 패키지 설치, 홈 설정 쓰기, 비밀값 환경 변수를 찾음 | 아래 표 7열 |
| 키트 형식 검사 | 채택 후보 스킬을 메모리로만 받아 `kit.skill_check.check(..., kit_rules=False)`를 두 에이전트로 실행 | §5.1 |

- 아무것도 clone, 설치, 실행하지 않았다. 내려받은 내용은 메모리와 스크래치 폴더에만 있었다.
- **확인 수준**:
  - "Codex·Claude 호환"은 파일 형식과 경로가 맞다는 **정적 판단**이다(UNVERIFIED-RUNTIME). 실제 에이전트가 스킬을 읽는지는 P6에서 확인한다.
  - 유지보수 판단은 커밋 날짜, 릴리스 날짜, 열린 이슈 수만 근거로 했다. 이슈에 얼마나 빨리 응답하는지는 보지 않았다.

### 결정 기준

| 결정 | 뜻 |
|---|---|
| `ADOPT-VENDOR` | 고정 커밋의 파일을 `third_party/`에 복사하고 `sources.lock.json`·NOTICES에 기록(P4-T4). 허용 라이선스(MIT/Apache-2.0/BSD)와 마크다운 위주, 키트가 실행하지 않는 것만 |
| `ADOPT-REFERENCE` | 파일은 복사하지 않음. 카탈로그나 문서에 고정된 링크·버전과 수동 opt-in 방법만 둠 |
| `DEFER` | 지금은 넣지 않음. 다시 볼 조건이나 Task를 적음 |
| `REJECT` | §14.3 위반이나 대체재가 있어 넣지 않음 |

## 1. 요약

| 결정 | 수(사용자 목록 49개 기준) | 항목 |
|---|---|---|
| ADOPT-VENDOR | 12 | U-01, U-04, U-05(대체안), U-06(5개, 2026-11-08), U-16, U-17(13개, 2026-11-08), U-22(7개, 2026-11-08), U-31(일부), U-32, U-33(3개, 2026-11-08), U-40(7개, 2026-11-06), U-49(일부) |
| ADOPT-REFERENCE | 12 | U-02, U-03, U-12, U-14, U-15, U-19, U-24, U-25, U-41, U-45, U-46, U-48 |
| DEFER | 20 | U-07, U-08, U-09, U-10, U-13, U-20, U-27, U-28, U-29, U-30, U-34, U-35, U-36, U-37, U-38, U-39, U-42, U-43, U-44, U-47 |
| MANUAL-GUIDE(검토자 결정 2026-11-06) | 1 | U-23 (`catalog/manual.json`, 키트는 실행하지 않음) |
| REJECT | 3 | U-11, U-18, U-21 |
| EXCLUDED(검토자 결정 2026-11-06) | 1 | U-26 |

2026-11-08 3단계(검토자 승인: MCP 서버, Claude 플러그인, 수동 도구, 원격 MCP 수동 안내, 문서 전용 링크, 평가 정정) 뒤의 분류다. 바뀐 항목과 이유는 §8.1에 있다.

| 결정 | 수 | 항목 |
|---|---|---|
| ADOPT-VENDOR | 12 | 위와 같음 |
| ADOPT-REFERENCE | 20 | U-02, U-03, U-09, U-12, U-13, U-14, U-15, U-19, U-24, U-25, U-27, U-28, U-29, U-34, U-39, U-41, U-43, U-46, U-47, U-48 |
| DEFER | 2 | U-30, U-38 |
| MANUAL-GUIDE | 11 | U-07, U-08, U-10, U-20, U-23, U-35, U-36, U-37, U-42, U-44, U-45 |
| REJECT | 3 | U-11, U-18, U-21 |
| EXCLUDED | 1 | U-26 |

목록 밖 항목:

| 항목 | 결정 |
|---|---|
| U-51 OMX | ADOPT-VENDOR. 마크다운만, **user 범위 전용**. Q6·REQ-USER-005 |
| `microsoft/playwright-mcp` | ADOPT-REFERENCE (P4-T5) |
| `modelcontextprotocol/servers`, `openai/skills`, `github/github-mcp-server` | DEFER |
| `openai/plugins` | ADOPT-REFERENCE |

**승인을 요청하는 채택안**(§4에 설치 계획과 보안 영향):

| # | 무엇 | 출처@고정 커밋 | 라이선스 | 위험 |
|---|---|---|---|---|
| A1 | superpowers 스킬 5개: `systematic-debugging`, `test-driven-development`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review` | `obra/superpowers@22f0b463e7a5e579904dd6211a520321035526f7` (태그 v7.0.2) | MIT | low |
| A2 | `frontend-design` | `anthropics/skills@ca45fc496a3436251f191354091d557da31c15b5` | Apache-2.0 (스킬 폴더 `LICENSE.txt`) | low |
| A3 | `emil-design-eng` | `emilkowalski/skills@c8a79627b59d72d764d6ab6f2c87c09a48169833` | MIT | low |
| A4 | `web-design-guidelines`. 키트가 SKILL.md를 새로 쓰고, 규칙 원문은 고정 사본을 씀 | `vercel-labs/web-interface-guidelines@434b7f91364665f2f733b310ec54809bf8f37937`의 `command.md` | MIT | low |
| A5 | OMX 스킬 29개(파일 30개) + prompts 32개 (마크다운만, user 범위) | `Yeachan-Heo/oh-my-codex@f7830d0ae1b5c39cb2a86937dabfc1bdd9b7f237` (태그 v0.21.46) | MIT | low(파일) / high(CLI, 키트가 설치하지 않음) |
| R1 | `@playwright/mcp@0.0.84`. MCP 카탈로그 항목, 기본 비활성 | `microsoft/playwright-mcp@3d49ff2615216fcef64fb7748d9f660d3c000ad7` | Apache-2.0 | medium |

## 2. 리소스별 사실 (기준 4·5·6·7)

- 커밋은 앞 12자리만 적었다. 전체 값은 evidence JSON에 있다.
- "push"는 기본 브랜치 HEAD의 커밋 날짜다.
- 위험: low는 마크다운만 있거나 실행되지 않는 경우다. medium은 로컬 스크립트, 로컬 서버, 넓은 파일 읽기가 있는 경우다. high는 다음 중 하나라도 있는 경우다.
  - 사용자 설정·훅을 바꾼다
  - 요청 경로를 중계한다
  - 비밀값이 필요하다
  - 외부로 송신한다
  - postinstall이 있다

| ID | 저장소@HEAD | 4. 라이선스(원문 확인) | 5. 유지보수 | 6. 의존성·설치 | 7. 권한·보안 → 위험 |
|---|---|---|---|---|---|
| U-01/U-31 | `anthropics/skills@ca45fc496a34` | 루트 LICENSE 없음. `THIRD_PARTY_NOTICES.md`가 있고 **스킬마다 `LICENSE.txt`**. `frontend-design`, `webapp-testing`은 Apache-2.0 원문 확인 | push 2026-10-28, 릴리스 없음, 이슈 1,485 | 없음(마크다운). `webapp-testing`은 Python Playwright | `frontend-design`: 마크다운 2개 → low. `mcp-builder`는 npx 안내 |
| U-02 | `nextlevelbuilder/ui-ux-pro-max-skill@b7d5353e0130` | MIT(LICENSE) | v2.15.0(2026-08-13), push 2026-11-05 | Python 스크립트 61개, CSV 90개, **글꼴 `.ttf` 54개**(글꼴 라이선스는 따로 확인 필요) | `fetch-background.py`가 원격에서 받음. API 키 환경 변수를 씀 → medium |
| U-03 | `Nutlope/hallmark@407fa689f4a2` | MIT(LICENSE) | push 2026-11-05, 릴리스 없음 | Node `.mjs` 15개, 이미지 50개 | `install-hook.mjs`가 `.claude/settings.json`(`--global`이면 `~/.claude/settings.json`)에 훅을 씀. 이미지 생성에 API 키 필요 → high |
| U-04 | `emilkowalski/skills@c8a79627b59d` | MIT(LICENSE) | push 2026-11-04, 이슈 1 | 없음(마크다운 26개) | 스크립트 없음 → low |
| U-05 | `vercel-labs/agent-skills@1a2c79d4e6c4` | 루트 LICENSE **없음**. README "License: MIT"만 있음 | push 2026-10-27 | 없음 | `web-design-guidelines`가 **쓸 때마다 `raw.githubusercontent.com/.../main/command.md`를 받아옴**(고정 안 됨, 네트워크) → medium. 규칙 원본 `vercel-labs/web-interface-guidelines@434b7f91`은 MIT(LICENSE, © 2025 Vercel Labs) |
| U-06 | `DietrichGebert/ponytail@96608e078b2d` | MIT | v5.3.3(2026-10-29) | npm, 의존성 0, 수명주기 없음 | 행동 지침 플러그인 → low |
| U-07 | `Graphify-Labs/graphify@16218bfc80d4` | Apache-2.0 | v0.9.103(2026-11-05), 이슈 1,616 | Python 도구 | `CLAUDE.md` 수정, PreToolUse 훅 → high **2026-11-08:** v0.9.104(`433a57a00290`). PyPI 이름은 `graphifyy`(y 두 개). README에 텔레메트리 없음 |
| U-08 | `headroomlabs-ai/headroom@2d3ee5184643` | Apache-2.0 | v0.43.1(2026-11-05) | 로컬 프록시 | 모델 요청을 중계 → high **2026-11-08:** 익명 텔레메트리 비콘이 **기본 켜짐**. `HEADROOM_TELEMETRY=off`, `HEADROOM_BEACON=off`, `DO_NOT_TRACK=1`, `HEADROOM_OFFLINE=1`로 끔(README) |
| U-09 | `HeyCubit/effortless@e5c590dfd940` | MIT | push 2026-10-23 | Claude Code mod | 홈 설정에 쓰고 API 키 환경 변수를 씀 → high **2026-11-08:** 고정 커밋 `7912a6ccdf0a`(플러그인 1.72.0). Haiku를 프롬프트마다 부름, 앱 안 Update 버튼이 고정을 우회, 설정 안내에 붙인 키는 `~/.config/jev/.env`에 평문 저장, 사용자 설정에 `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` 필요 |
| U-10 | `mvschwarz/openrig@bd39da9872af` | Apache-2.0 | v0.7.8(2026-11-05) | npm(수명주기 없음), tmux | 셸 세션 제어. Windows에서 tmux 없음 → medium **2026-11-08:** v0.7.9(`ddb9d25be74a`). 네이티브 Windows 미지원(WSL2만). `rig setup`이 `~/.tmux.conf`, `~/.codex/config.toml`, `~/.claude.json`, `~/.claude/skills`, `~/.agents/skills`에 씀 |
| U-11 | `trailhq/Trail-Code@ca20a67764e9` | MIT | push 2026-11-03 | npm `@nanonets/graft`. **`postinstall`과 `prepare`가 있음**. `prepare`가 배포본에 PostHog 텔레메트리 키를 넣음 | 훅, 텔레메트리 → high |
| U-12 | `msitarzewski/agency-agents@b37b5bb33b78` | MIT | push 2026-10-25 | 마크다운 384개(에이전트 정의) | low. 다만 양이 많음 |
| U-13 | `DeusData/codebase-memory-mcp@612eee2518ef` | MIT | v0.12.1(2026-10-16), 이슈 550 | 네이티브 바이너리 MCP | 저장소 전체를 색인 → medium **2026-11-08 정정:** npm 패키지에 `postinstall`이 있어 PyPI `uvx codebase-memory-mcp==0.12.1`을 씀. 첫 실행 때 GitHub Releases에서 네이티브 바이너리를 받고 데몬을 띄움(캐시 `~/.cache/codebase-memory-mcp`). `install` 하위 명령은 쓰지 않음. lock 커밋 `a7158ac2f48c`(태그 v0.12.1) |
| U-14 | `calesthio/OpenMontage@d21f5d4eaa08` | **AGPL-3.0** | push 2026-11-03 | — | 레포에 넣으면 AGPL 의무가 생김 **2026-11-08 정정:** 저장소가 `OpenMontageInc/OpenMontage`로 옮겨짐. AGPL-3.0 그대로 |
| U-15 | `f/prompts.chat@06539cb86bd2` | 이중 라이선스(코드 MIT, 프롬프트 CC0. LICENSE·LICENSE-MIT·LICENSE-CC0 원문 확인) | push 2026-11-05 | Next.js 앱, `postinstall: prisma generate` | 웹 앱 → 설치 대상이 아님 **2026-11-08:** HEAD `ba34d09010de` |
| U-16/U-32 | `multica-ai/andrej-karpathy-skills@2c606141936f` | 루트 LICENSE **없음**. README "License: MIT", 스킬 frontmatter `license: MIT`. **저작권 표시 문구가 없음** | push 2026-04-20(7개월 전) | 마크다운 | low |
| U-17 | `cloudflare/skills@1f2cd0a19588` | Apache-2.0 | push 2026-11-03 | 스킬 19개가 `npx wrangler`를 씀 | Cloudflare 토큰, 배포(외부 쓰기) → high |
| U-18 | `charmbracelet/mods@0425d0d7861e` | MIT | **보관됨(archived)**. 마지막 릴리스 v1.8.1(2025-07-10) | Go CLI | — |
| U-19 | `mksglu/context-mode@7bad9ac3501f` | **Elastic License 2.0**(원문 확인. OSI 오픈소스 아님) | v2.1.4(2026-11-05) | npm, 훅 | 훅이 도구 출력을 가로챔 → high **2026-11-08:** v2.1.6 |
| U-20 | `rtk-ai/rtk@8268663fac0b` | Apache-2.0 | v1.1.0(2026-10-25), 이슈 1,711 | Rust 바이너리, 셸 훅 | 셸 명령을 다시 씀 → high **2026-11-08 정정:** 라이선스가 **섞여 있음**: 기본 `rtk` 바이너리는 Apache-2.0 + BUSL-1.1, `rtk-oss`는 Apache-2.0만, `rtk-proxy`는 BUSL-1.1. 텔레메트리는 기본 꺼짐(README). v1.1.0 커밋 `753a3b0e939f` |
| U-21 | `vercel-labs/skills@cad8cda44e89` | MIT | v1.7.6(2026-11-03) | `find-skills`가 `npx skills add <임의 저장소>`를 안내 | 고정되지 않은 외부 스킬 설치 → high |
| U-22 | `affaan-m/ECC@b38be6a7f635` | MIT | v2.2.3(2026-10-01) | npm 의존성 5. 훅·에이전트·스킬 대량 | high(훅) |
| U-23 | `musistudio/claude-code-router@057abaa1f955` (2026-11-06 재선정; 이전 후보 `weave-os/router`) | MIT | push 2026-10-10. npm `@musistudio/claude-code-router@3.1.3`, bin `ccr`. 설치 스크립트(pre/post/install, prepare) 없음 | 로컬 프록시가 Claude Code 요청을 다른 모델 제공자로 중계 | 코드·프롬프트가 외부 제공자로 나감, 제공자 API 키 필요, Claude Code의 요청 주소를 바꿈 → high |
| U-24 | `KasperZutterman/Second-Brain@4302f25c60f5` (2026-11-06 재선정; 이전 후보 `NicholasSpisak/second-brain`) | MIT | push 2026-10-14 | 파일은 README와 LICENSE뿐(링크 모음) | 실행할 것이 없음 → low **2026-11-08:** HEAD `4302f25c60f5` 그대로 |
| U-25 | `google-research/harness2@686881751887` | Apache-2.0 | push 2026-11-02 | Python 연구 도구 | medium **2026-11-08:** Linux 전용. HEAD `686881751887` 그대로 |
| U-26 | 제외(검토자 결정 2026-11-06) | — | — | — | — |
| U-27 | `JohnnyVizz/claude-kit@c871c153ead5` | MIT | push 2026-10-12 | Claude Code mod | 홈 설정에 씀 → medium **2026-11-08 정정:** 고정 커밋의 코드에서 홈 설정 쓰기와 네트워크 호출을 찾지 못함. 플러그인 1.2.1. mod라서 medium 유지 |
| U-28 | `data-goblin/claude-code-filetree@2b42d0faf707` | MIT | v0.8.0(2026-11-05). Claude Code 2.1.287 이상 필요 | mod | 홈 설정에 쓰고 원격 호출이 있음 → medium **2026-11-08 정정:** 홈 설정 쓰기·네트워크 호출을 찾지 못함. v0.8.2(`a3d36b1a56c0`)는 Claude Code **2.1.306** 이상 필요 |
| U-29 | `anthropics/claude-code-playground@569c5283d9a0`의 `claude-code/mods/replay-theater` | Apache-2.0 | push 2026-10-01 | mod: `hooks/hooks.json` + `replay-theater.mjs` | 훅 → medium **2026-11-08:** 플러그인 0.1.0, 루트 LICENSE Apache-2.0 원문 확인. Claude Code 2.1.287 이상 |
| U-30 | `JuliusBrussee/caveman@ca3a524022a9` | Apache-2.0 | v4.0.1(2026-10-13) | 스킬 22개 + `.codex/hooks.json` + `src/hooks/*` | 세션 시작 훅. 설명이 YAML 여러 줄 블록(§5.2) → medium |
| U-33 | `mattpocock/skills@4ae2317ddb22` | MIT | v1.3.2(2026-10-29) | 스킬 39개 | 일부가 git 훅·pre-commit을 설치 → medium |
| U-34 | `morluto/rea@a7574d427472` | MIT | rea-agents 6.8.0(2026-10-25), 이슈 1,621 | npm 의존성 42, `prepare` | 사용자 홈에 자동 설치 → high **2026-11-08 정정:** 홈 자동 설치는 `rea-agents setup`일 때뿐이고, `rea-agents mcp`로 **프로젝트 범위 stdio 서버**를 띄울 수 있음. lock 커밋 `160d821ac9a0`(6.8.0, package.json 확인) |
| U-35~U-38 | Mobbin, Nicelydone, Refero, Lazyweb 원격 MCP | 서비스 약관(유료·OAuth·토큰) | — | 원격 HTTP | 외부 송신, 비밀값 → high **2026-11-08:** Mobbin `https://api.mobbin.com/mcp`(OAuth, 공식 문서의 Claude Code 명령 확인), Nicelydone `https://mcp.nicelydone.club/mcp`(OAuth 2.1), Refero `https://api.refero.design/mcp`(OAuth 또는 Bearer 토큰 헤더). Lazyweb은 엔드포인트를 공식 문서에서 찾지 못함(UNVERIFIED) |
| U-39 | `Nutlope/inspo@022f80977c1e` | MIT | push 2026-10-28, 버전 0.0.0(배포본 없음) | npm | 고정할 버전이 없음 → medium **2026-11-08 정정:** npm `inspo-mcp@0.2.0`이 배포되어 **고정할 수 있음**(gitHead `022f80977c1e`). 첫 실행 때 약 14 MB 카탈로그를 Vercel Blob에서 받음. 선택 키 `TOGETHER_API_KEY`(키 발급 페이지는 UNVERIFIED) |
| U-40 | `K-Dense-AI/scientific-agent-skills@a25cf9ec00e2` | MIT(LICENSE.md) | v2.72.0(2026-10-01) | 스킬 **177개**(`skills/`) | 스킬마다 다름. 일부는 API 키를 씀 |
| U-41 | `wheresryan22/anatomy@1482e8469b0a` | MIT | v1.1.0(2026-10-12) | SKILL.md 1개(186줄, 설명 1,018자) | low |
| U-42 | `thedotmack/claude-mem@89b97644e39d` | Apache-2.0 | v15.10.0(2026-11-05) | 플러그인과 훅, 로컬 DB | 세션 내용을 저장 → high **2026-11-08:** v15.12.0(`eb00299a6a74`). 사용 분석이 **기본 켜짐**(`npx claude-mem telemetry disable`), 설치기가 Bun·uv를 자동 설치 |
| U-43 | `microsoft/markitdown@7482c092d9c0` | MIT | v0.1.9(2026-10-21) | pip, `markitdown-mcp` | 파일 읽기, URL 변환 → medium **2026-11-08 정정:** MCP는 `markitdown-mcp==0.0.1a8`(알파), 커밋 `21d9c1d01ecc`(markitdown v0.1.9). 아무 파일이나 읽고 아무 URL이나 받으므로 **high** |
| U-44 | `ruvnet/ruflo@722232566ad1` | MIT | v3.72.0(2026-11-06) | npm `claude-flow`, 의존성 26 | 설정, 훅, 데몬 → high **2026-11-08:** v3.72.2(`b7bc909d5f0d`). `ruflo init`이 `.claude/`, `.claude-flow/`, `CLAUDE.md`, 설정을 프로젝트에 씀 |
| U-45 | `devlikemasta/bureau-des-agents@184daa898cbb` | MIT | v0.1.0(2026-10-14), ★60 | 로컬 웹 앱 | medium |
| U-46 | `anthropics/claude-plugins-official@ff920a4094a3`의 `plugins/security-guidance` | Apache-2.0 | push 2026-11-06 | Python 훅 67개 | SessionStart 훅이 `~/.claude/security/agent-sdk-venv`를 만들고 SDK를 pip로 설치함. Stop 훅이 git diff를 **LLM API로 보냄**(`ANTHROPIC_API_KEY`) → high **2026-11-08 정정:** 키트 고정 `ff920a4094a3`(2.0.17)은 HEAD보다 **한 버전 뒤**다. HEAD의 2.0.18은 훅이 바뀌어 diff를 검토한 뒤에만 올림 |
| U-47 | `D4Vinci/Scrapling@bc602488b44e` | BSD-3-Clause | v0.5.1(2026-11-04) | pip, 브라우저 | 웹 수집(외부 송신) → high **2026-11-08:** v0.5.1. MCP를 띄우려면 Python 패키지와 `scrapling install`(브라우저 다운로드)이 먼저 필요 |
| U-48 | `anthropics/knowledge-work-plugins@d900840716eb` | Apache-2.0 | push 2026-11-04 | Claude(Cowork) 플러그인 | 업무 커넥터 → medium |
| U-49 | `obra/superpowers@22f0b463e7a5` (= v7.0.2) | MIT(© 2025 Jesse Vincent) | v7.0.2(2026-11-03), 이슈 336 | 스킬 15개 + 세션 시작 훅(`hooks/session-start`) | 아래 스킬 5개는 마크다운 + 예시 파일만 → low. `brainstorming`은 로컬 서버를 띄움(127.0.0.1) → medium |
| U-51 | `Yeachan-Heo/oh-my-codex@509a299d586b`, 태그 v0.21.46 = `f7830d0ae1b5` | MIT(© 2026 Yeachan-Heo) | v0.21.46(2026-11-02) | npm CLI: **`postinstall`과 `prepare`가 있음**. 태그 커밋 기준 스킬 29개, prompts 32개 | 마크다운 → low. CLI와 훅 → high |
| S-MCP | `modelcontextprotocol/servers@36380287ed3b` | LICENSE 원문: **MIT에서 Apache-2.0으로 전환 중**(새 코드는 Apache-2.0) | v2.3.0(2026-11-04) | npx/uvx | 서버마다 다름 |
| S-OAI-SK | `openai/skills@49f948faa925` | 루트 없음. README: "스킬 폴더의 `LICENSE.txt`" | push 2026-06-24 | 스킬 44개 | 다수가 토큰과 외부 서비스를 씀 |
| S-OAI-PL | `openai/plugins@b767f8fa3be1` | 루트 LICENSE·README 언급 없음 | push 2026-11-03 | Codex 플러그인 60여 개 | 커넥터 위주 |
| S-PW | `microsoft/playwright-mcp@3d49ff261521` | Apache-2.0 | v0.0.84(2026-10-31), 이슈 2 | npm `@playwright/mcp`, 의존성 2, **수명주기 스크립트 없음**. 첫 실행 때 브라우저를 내려받음 | 지정한 URL로 브라우저를 엶(외부 접속) → medium |
| S-GH | `github/github-mcp-server@99d6d6503a7b` | MIT | v2.1.0(2026-11-03) | Go 바이너리 / Docker | GitHub 토큰, 쓰기 권한 → high |

## 3. 리소스별 판단 (기준 1·2·3·8·9와 결정)

- Codex와 Claude 열의 "그대로"는 `SKILL.md` 형식이 두 에이전트에서 같고, 키트가 `.agents/skills/` 또는 `.claude/skills/`로 복사만 하면 된다는 뜻이다.
- 프로필 이름 fullstack, ai-research는 P4-T6에서 만든다.

| ID | 1. 기능·프로필 | 2. Codex | 3. Claude | 8. 기존 스킬과 겹침 | 9. 활용·컨텍스트 비용 | 결정과 근거 |
|---|---|---|---|---|---|---|
| U-01 | UI 미적 방향, web/fullstack | 그대로 | 그대로(원래 Claude용) | 없음. 디자인 묶음에서 1순위(§3.1) | 새 UI를 만들 때. 72줄 | **ADOPT-VENDOR**(A2). 공식, 마크다운, Apache 원문이 스킬 폴더에 있음 |
| U-02 | 디자인 시스템 데이터 검색 | 스크립트 실행 필요 | `.claude/skills` 형식 | U-01과 겹침 | 데이터가 크고 글꼴 54개 | **ADOPT-REFERENCE**. 스크립트, 원격 호출, 글꼴 라이선스 확인 부담. 링크만 둠 |
| U-03 | 디자인 + 이미지 생성 | 그대로(스크립트는 Node) | 그대로 | U-01과 겹침 | API 키가 필요함 | **ADOPT-REFERENCE**. 훅을 설치하는 스크립트(설정 쓰기)와 API 키 |
| U-04 | 인터랙션·애니메이션 다듬기, web/fullstack | 그대로 | 그대로 | U-01과 역할이 다름(동작·세부) | 677줄. 500줄 권장 초과는 경고만 | **ADOPT-VENDOR**(A3). `emil-design-eng` 1개만. 나머지 16개는 필요해지면 `kit source add` **2026-11-08 검토자 승인:** 나머지 16개를 opt-in 팩 `motion`(standard만)으로 `kit source add`(같은 커밋). REVIEW 10건(방어 문구 5, 중첩 코드 펜스 앞 U+200B 4, 이모지 안 U+200D 1)을 줄마다 확인해 무해로 보고 `--accept-risk` |
| U-05 | UI 코드 가이드라인 리뷰, web/fullstack | 그대로 | 그대로 | `design-review`(구조 리뷰)와 대상이 다름 | 리뷰할 때. 규칙 8 KB | 원본 스킬은 **REJECT**: 쓸 때마다 고정되지 않은 URL을 받음(§14.3), LICENSE 파일 없음. **대체안 ADOPT-VENDOR**(A4): 규칙 원문을 고정 커밋으로 `references/`에 두고 SKILL.md는 키트가 씀(origin `adapted`) |
| U-06 | "덜 쓰기" 행동 지침 | 그대로 | 플러그인 | standard 정책·karpathy와 겹침 | 낮음 | **ADOPT-REFERENCE**. 정책 파일과 중복 **2026-11-08 검토자 승인:** opt-in 팩 `lean`(standard만)으로 5개 `kit source add`. `ponytail-help`는 뺌(전역 `npm install -g …@latest`·`brew` 안내, 플러그인 전용 명령) |
| U-07 | 코드 지식 그래프 | 스킬 + 도구 | 훅 | `codebase-explorer` | 큰 저장소에서 유용 | **DEFER**. 정책 파일을 수정하고 훅을 씀. 큰 저장소용 opt-in 팩을 설계할 때 다시 봄(P4-T5 이후) **2026-11-08 3단계: MANUAL-GUIDE**(`catalog/manual.json` `graphify` 0.9.104). 정책 파일·훅을 쓰므로 키트는 실행하지 않고 프로젝트 범위 설치(`graphify install --project`)와 `graphify uninstall`을 안내 |
| U-08 | 컨텍스트 압축 프록시 | 프록시 | 프록시 | — | — | **DEFER**. 요청 경로 중계 → 자동 활성화 금지. 사용자 범위 수동 도구로만 검토 **2026-11-08 3단계: MANUAL-GUIDE**(`headroom` 0.43.1). 요청 경로 중계라 자동 활성화 금지는 그대로. 텔레메트리 끄는 환경 변수를 첫 단계로 안내 |
| U-09 | 추론 노력 자동 선택(Claude mod) | 해당 없음 | mod | — | — | **DEFER**(P4-T5 Claude mod 카탈로그) **2026-11-08 3단계: ADOPT-REFERENCE**(`catalog/plugins.json` `effortless`, high, 기본 꺼짐, `--plugin effortless`). 선택 키 `TYPESAFE_API_KEY`는 이름만 |
| U-10 | tmux 다중 에이전트 | 도구 | 도구 | 오케스트레이션 묶음 | Windows에 tmux 없음 | **DEFER**. 이 PC(Windows)에서 쓸 수 없음 **2026-11-08 3단계: MANUAL-GUIDE**(`openrig` 0.7.9). 이 PC(Windows)에서는 WSL2가 필요. 되돌리기는 상류 문서가 일부뿐이라 그렇게 적음 |
| U-11 | 공유 코드 메모리 | 도구 + 훅 | 도구 + 훅 | `codebase-explorer` | — | **REJECT**. `postinstall`, 배포본 텔레메트리 키(§14.3). 대안은 U-13(DEFER) |
| U-12 | 역할별 에이전트 정의 384개 | 변환 필요(Codex agents 형식 다름) | `.claude/agents` | 오케스트레이션 묶음 | 매우 큼 | **ADOPT-REFERENCE** |
| U-13 | 코드 색인 MCP | MCP | MCP | `codebase-explorer` | 큰 저장소 | **DEFER**(P4-T5 MCP 카탈로그에서 바이너리 고정·해시를 확인한 뒤 opt-in 후보) **2026-11-08 3단계: ADOPT-REFERENCE**(`catalog/mcp.json` `codebase-memory`, medium, 기본 꺼짐, `--mcp codebase-memory`). npm 대신 uvx |
| U-14 | 영상 편집 에이전트 | — | — | — | 개발 키트와 무관 | **ADOPT-REFERENCE**(링크만). AGPL이라 복사 불가 **2026-11-08:** 링크만(§8.1 문서 전용 목록). 새 주소 `OpenMontageInc/OpenMontage` |
| U-15 | 프롬프트 모음 | — | — | — | — | **ADOPT-REFERENCE**. 설치 대상이 아님 **2026-11-08:** 링크만(§8.1 문서 전용 목록) |
| U-16 | 행동 지침 CLAUDE.md | AGENTS.md로 옮겨야 함 | 그대로 | `shared/policies/standard.md`와 대부분 겹침(단순성, 가정 밝히기, 수술적 변경, 검증 기준) | 짧음 | **ADOPT-VENDOR**(A6, Q2 결정). 저작권 표시가 없다는 사실을 NOTICES에 그대로 적는다 |
| U-17 | Cloudflare 배포 | 그대로 | 그대로 | — | Cloudflare를 쓸 때만 | **DEFER**. 토큰, 배포 쓰기. fullstack 프로필의 opt-in 팩 후보(P4-T6) **2026-11-08 검토자 승인:** opt-in 팩 `cloudflare`(standard만)로 13개 `kit source add`. 뺀 것: `basin`(`references/sql/configuration.md:27`이 토큰을 프로젝트 `.env` 파일에 두라고 안내), `cf-cli`(전역 npm 설치, 사용자 AGENTS.md/CLAUDE.md 수정 안내), `turnstile-spin`(API 토큰을 `~/.cf-turnstile-token`에 저장, `~/.claude/skills` 링크), `web-perf`(`@latest` MCP), `nextjs-on-cloudflare`(묻지 않고 `npx skills add`), `cloudflare-email-service`(묻지 않고 도메인 발송 활성화), 그리고 이들로 링크가 걸린 `cloudflare`, `cloudflare-one`, `gateway-workers` |
| U-18 | 터미널 LLM CLI | — | — | — | — | **REJECT**. 보관된 저장소이고 에이전트 스킬이 아님 |
| U-19 | 도구 출력 압축 | 플러그인 | 플러그인 | 컨텍스트 묶음 | — | **ADOPT-REFERENCE**. ELv2(허용 라이선스 아님), 훅 **2026-11-08 3단계:** 플러그인으로 **넣지 않음**. ELv2는 키트 라이선스 표(`kit/source_add.py` `ALLOWED`)에 없고 `other`로 분류되어 `--accept-license` 없이는 복사도 안 되는 라이선스다. 플러그인 카탈로그는 사용자 PC에 설치까지 이어지므로 같은 기준을 적용해 참조(링크)만 둔다 |
| U-20 | 셸 출력 압축 | 훅 | 훅 | 컨텍스트 묶음 | — | **DEFER**. 셸 훅 → 자동 금지 **2026-11-08 3단계: MANUAL-GUIDE**(`rtk`, `rtk-oss` 1.1.0을 권장). 셸 훅이라 키트는 실행하지 않음 |
| U-21 | 스킬 검색·설치 | 그대로 | 그대로 | P4-T8 `add-skill-source`와 같은 목적 | — | **REJECT**. 고정되지 않은 외부 설치로 `sources.lock.json`을 우회함. `add-skill-source`가 대체 |
| U-22 | 모든 것 모음 | 일부 | 플러그인 | 거의 모든 레포 스킬 | 매우 큼 | **ADOPT-REFERENCE**. 필요한 스킬만 나중에 `kit source add` **2026-11-08 검토자 승인:** opt-in 팩 `eng-patterns`(standard만)로 7개 `kit source add`. `docker-patterns`는 뺌(ECC 전용 하네스, 컨테이너 안 `npm install --global`, OAuth 자격 증명 중계) |
| U-23 | 모델 라우터(claude-code-router) | — | 수동 안내 | — | — | **MANUAL-GUIDE**(**검토자 결정(2026-11-06)**: "수동 안내만"). `catalog/manual.json`의 `claude-code-router` 3.1.3. `kit install/plan --manual claude-code-router`가 설치·키 설정·되돌리기 단계와 위험을 출력만 하고, 키트는 실행·설치하지 않음 |
| U-24 | Second Brain 링크 모음 | — | — | — | 개인 지식 관리 | **ADOPT-REFERENCE**. 설치할 파일이 없는 링크 모음 **2026-11-08:** 링크만(§8.1 문서 전용 목록) |
| U-25 | 하네스 최적화 연구 | — | — | — | ai-research | **ADOPT-REFERENCE** **2026-11-08:** 링크만(§8.1 문서 전용 목록). Linux 전용 |
| U-26 | — | — | — | — | — | **EXCLUDED**(검토자 결정) |
| U-27/U-28/U-29 | Claude Code mods(진행 표시, 파일 트리, 세션 재생) | 해당 없음 | mod·훅 | — | 편의 기능 | **DEFER**(P4-T5 Claude 플러그인·mod 카탈로그. 훅은 기본 비활성, opt-in) **2026-11-08 3단계: ADOPT-REFERENCE**. `catalog/plugins.json`의 `savvy-progress`, `filetree`, `replay-theater`(Claude만, medium, 기본 꺼짐, `--plugin NAME`) |
| U-30 | 짧게 말하기 | 훅 | 훅 | 정책 파일의 보고 형식과 충돌할 수 있음 | 토큰 절약 | **DEFER**. 세션 훅. 키트 파서가 여러 줄 설명을 아직 못 읽음(§5.2) |
| U-31 | Anthropic 스킬 모음 | 그대로 | 그대로 | — | — | **ADOPT-VENDOR(일부)** = U-01. `webapp-testing`은 R1과 비교한 뒤 DEFER. `skill-creator`, `mcp-builder`는 개발 키트 범위 밖 → REFERENCE **2026-11-08:** 승인된 팩 `agent-dev`(`skill-creator`, `mcp-builder`)와 `web-testing`(`webapp-testing`)은 위험 검토에서 경계 사례로 빼고 검토자 결정을 기다린다. 핵심 단계가 빠지는 스크립트(`scripts/*.py`)를 실행하고, `mcp-builder`는 venv 없는 `pip install`을 안내한다 |
| U-32 | = U-16 | | | | | **ADOPT-VENDOR**(U-16과 같음, A6) |
| U-33 | 엔지니어링 스킬 39개 | 그대로 | 그대로 | `tdd`, `diagnosing-bugs`, `code-review`가 superpowers·레포 스킬과 겹침 | 큼 | **ADOPT-REFERENCE**. 겹치는 부분은 superpowers(A1)를 고름(§3.2) **2026-11-08 검토자 승인:** opt-in 팩 `planning-extras`(standard만)로 `domain-modeling`, `to-spec`, `handoff` `kit source add`. `grill-me`(없는 `grilling` 스킬만 부름)와 `triage`(외부 PR을 체크아웃해 테스트 실행)는 뺌 |
| U-34 | 에이전트 런타임 | 도구 | 도구 | 오케스트레이션 | — | **DEFER**. 홈 자동 설치, `prepare` **2026-11-08 3단계: ADOPT-REFERENCE**(`catalog/mcp.json` `rea`, high, 기본 꺼짐, `--mcp rea`). `rea-agents setup`은 절대 실행하지 않음 |
| U-35~U-38 | 디자인 레퍼런스 원격 MCP | 원격 MCP | 원격 MCP | — | 유료 계정이 있을 때 | **DEFER**. 원격 MCP는 기본 거부(§15). P4-T5에서 원격 opt-in과 경고를 설계한 뒤 다시 봄 **2026-11-08 3단계:** U-35 Mobbin, U-36 Nicelydone, U-37 Refero는 **MANUAL-GUIDE**(`catalog/manual.json`, `claude mcp add --transport http <name> <url>`을 사람이 실행, OAuth). `catalog/mcp.json`에는 넣지 않음(§15). U-38 Lazyweb은 엔드포인트를 확인하지 못해 **DEFER 유지** |
| U-39 | 디자인 레퍼런스 MCP | MCP | MCP | U-35~U-38 | — | **DEFER**. 배포된 버전이 없어 고정할 수 없음 **2026-11-08 3단계: ADOPT-REFERENCE**(`catalog/mcp.json` `inspo` 0.2.0, medium, 선택 키가 있어 기본 꺼짐, `--mcp inspo`) |
| U-40 | 과학 연구 스킬 177개 중 7개 | 그대로 | 그대로 | — | ai-research | **ADOPT-VENDOR**(**검토자 결정(2026-11-06)**: "7개 모두 vendor"). `kit source add`로 `third_party/K-Dense-AI-scientific-agent-skills/`에 반영(lock id `k-dense-ai-scientific-agent-skills`, 커밋 `a25cf9ec00e2`). 새 팩 `research`(standard 전용)를 `ai-research` 프로필에 넣음. 스크립트는 빼고, `pytorch-lightning`의 템플릿 3개만 문서 링크 때문에 `--include` |
| U-41 | 기계 일러스트 그리기 | 그대로 | 그대로 | — | 드묾 | **ADOPT-REFERENCE** |
| U-42 | 세션 메모리 | 훅 | 플러그인 + 훅 | — | — | **DEFER**. 세션 내용을 저장 **2026-11-08 3단계: MANUAL-GUIDE**(`claude-mem` 15.12.0). 분석 끄기를 단계에 넣음. 되돌리기는 상류 문서가 일부뿐 |
| U-43 | 문서를 마크다운으로 변환 | MCP/CLI | MCP/CLI | — | data, ai-research | **DEFER**(P4-T5에서 `markitdown-mcp` 버전 고정 후 opt-in 후보) **2026-11-08 3단계: ADOPT-REFERENCE**(`catalog/mcp.json` `markitdown`, high, 기본 꺼짐, `--mcp markitdown`) |
| U-44 | 오케스트레이션 플랫폼 | 도구 | 도구 | 오케스트레이션 | — | **DEFER**. 훅과 데몬 **2026-11-08 3단계: MANUAL-GUIDE**(`ruflo` 3.72.2, 상류 예시는 `@latest`라 버전을 직접 고정). 되돌리기는 상류 문서가 일부뿐 |
| U-45 | 에이전트 사무실 UI | — | — | — | — | **ADOPT-REFERENCE** **2026-11-08 3단계: MANUAL-GUIDE**(`bureau-des-agents` 0.1.0, 커밋 고정 clone) |
| U-46 | 보안 경고와 LLM 리뷰 | 해당 없음 | 플러그인(훅) | — | 보안 리뷰 | **ADOPT-REFERENCE**. 플러그인 카탈로그에 수동 opt-in 방법만 둠. 훅이 venv·pip 설치를 하고 diff를 API로 보내므로 자동 설치 금지 **2026-11-08:** 고정은 그대로(2.0.17). 2.0.18 훅 변경을 검토하기 전에는 올리지 않음 |
| U-47 | 웹 스크래핑 | MCP | MCP | — | — | **DEFER**. 외부 송신 **2026-11-08 3단계: ADOPT-REFERENCE(목록만)**. `catalog/mcp.json` `scrapling`, 실행 명령 없음, high |
| U-48 | 업무용 플러그인 | 해당 없음 | 플러그인 | — | 개발 범위 밖 | **ADOPT-REFERENCE** |
| U-49 | 개발 방법론 | 그대로 | 그대로(원래 Claude 플러그인) | 레포 스킬 4쌍(§3.2) | 매일 씀 | **ADOPT-VENDOR(일부)**(A1 + 계획 체인 6개는 opt-in 팩 A7, Q1 결정) |
| U-51 | Codex 워크플로(OMX) | 그대로 | 해당 없음 | 오케스트레이션 | 이 PC 전역에서 이미 씀 | **ADOPT-VENDOR**(A5). 마크다운만, user 범위만. npm CLI는 설치하지 않고 수동 명령만 출력 |
| S-MCP | 공식 MCP 서버 | | | 기존 `mcp/manifest.json` | | **DEFER**(P4-T5). 기존 판단(fetch/git/filesystem 비활성)을 유지하고 standard 정책에서 다시 평가 |
| S-OAI-SK | OpenAI 스킬 | 그대로 | 그대로 | `playwright`, `security-*`가 R1·U-46과 겹침 | | **DEFER**. 스킬마다 LICENSE.txt를 확인해야 함. 필요할 때 `kit source add` |
| S-OAI-PL | OpenAI 플러그인 | 플러그인 | 해당 없음 | | | **ADOPT-REFERENCE**. 루트 라이선스 없음 |
| S-PW | 브라우저 테스트 MCP, web/fullstack | MCP(TOML) | MCP(`.mcp.json`) | 없음 | E2E 확인 | **ADOPT-REFERENCE**(R1). P4-T5 카탈로그에 `@playwright/mcp@0.0.84`. 기본 비활성, opt-in |
| S-C7 | 라이브러리 문서 조회 MCP(context7) | MCP(TOML) | MCP(`.mcp.json`) | 없음 | 최신 문서 | **ADOPT-REFERENCE**(**검토자 결정(2026-11-06)**: P4-T9 b 승인). `@upstash/context7-mcp@4.5.1`, MIT, 커밋 `5e4df8d22231`, 패키지와 직접 의존성 12개에 설치 스크립트 없음(npm view). 기본 꺼짐(`--mcp context7`), 조회한 라이브러리 이름과 질문이 context7.com으로 나감 → medium. 선택 키 `CONTEXT7_API_KEY`는 이름만 참조 |
| S-GH | GitHub MCP | | | | | **DEFER**. 토큰, 쓰기 권한 → high |

### 3.1 기능이 겹치는 묶음 비교 (REQ-SRC-005, §14.3 "하나만 고른다")

| 묶음 | 후보 | 고른 것 | 이유 |
|---|---|---|---|
| 디자인 방향 | U-01, U-02, U-03 | **U-01** | 공식, 마크다운 2개, 스크립트·키 없음. U-02는 스크립트·글꼴, U-03은 훅 설치·API 키 |
| 인터랙션 세부 | U-04 | **U-04**(`emil-design-eng`만) | 겹치는 후보 없음 |
| UI 리뷰 규칙 | U-05 | **U-05 대체안(A4)** | 원본은 실행 때마다 고정되지 않은 원격 규칙을 받음 |
| 디자인 레퍼런스 MCP | U-35~U-39 | 없음(DEFER) | 모두 원격·유료이거나 버전 없음 |
| 컨텍스트 절약 | U-06, U-08, U-19, U-20, U-30 | 없음(U-06은 REFERENCE) | 모두 훅·프록시이거나 정책과 겹침. 키트 정책 파일로 충분 |
| 코드 색인·메모리 | U-07, U-11, U-13, U-42 | 없음. 레포 `codebase-explorer` 유지 | 기존 스킬로 충분(§14.3). 큰 저장소용 opt-in은 U-13이 1순위(MIT, 훅 없음) |
| 오케스트레이션 | U-10, U-12, U-22, U-44, U-45, U-51 | **U-51**(user 범위) | 이미 이 PC에서 쓰고 Q6으로 결정됨. 나머지는 훅, 데몬, Windows 미지원 |
| 모델 라우팅 | U-09, U-23 | 없음 | 키·중계 |
| Claude mods | U-27, U-28, U-29 | 없음(P4-T5에서 opt-in 카탈로그) | 모두 훅 |
| 행동 지침 | U-16/U-32, U-06, 정책 파일 | **정책 파일**(평가 당시 `shared/policies/standard.md`, P4-T6부터 `shared/policies/` 모듈) | 내용 대부분이 이미 들어 있음 |
| 개발 방법론 | U-49, U-33, U-22, 레포 스킬 | **U-49**(A1) | 사용자가 이미 쓰고, 마크다운이며 서로 독립적임 |

### 3.2 레포 기존 스킬과 쌍별 겹침 (REQ-SRC-007)

- 모든 경우에 restricted 경로(서브커맨드 없음 포함)는 기존 11개를 그대로 설치한다.
- 아래 "standard 경로"는 새 경로(`--policy standard`, 기본값)에 해당한다.
- 구현은 카탈로그의 `policies`와 `replaces`로 한다(P4-T1에서 만든 필드).

| 레포 스킬 | 외부 스킬 | 차이 | standard 경로 처리 |
|---|---|---|---|
| `systematic-debugging`(27줄) | superpowers `systematic-debugging`(284줄 + 참고 파일 4개) | 같은 4단계 방법. 외부판이 근거 추적, 다층 방어, 오염 테스트 찾기까지 더 깊음 | **외부판으로 교체**. 레포판은 `policies: ["restricted"]` |
| `tdd-automator`(30줄) | superpowers `test-driven-development` | 레포판에만 "과제 예시·경계값에서 테스트를 먼저 만든다"가 있음 | **외부판으로 교체 + 레포 고유 문단은 overlay `.append`**(P4-T4에서 diff 제시) |
| `submission-validator`(25줄) | superpowers `verification-before-completion` | 외부판: 주장 전에 증거. 레포판: TASK_BRIEF 요구사항, 파일명·형식, 디버그 출력 잔여 점검 | **외부판으로 교체 + 레포 고유 점검은 overlay `.append`** |
| `implementation-review`, `design-review` | superpowers `requesting-code-review`, `receiving-code-review` | 레포판은 사용자가 부르는 설명·구조 리뷰. 외부판은 diff를 리뷰 서브에이전트에 맡기고 피드백을 검증함 | **둘 다 유지**(기능이 다름). 외부판 2개를 추가 |
| `task-router` | superpowers `brainstorming`, `writing-plans` | 레포판은 TASK_BRIEF 작성과 스킬 선택. 외부판은 설계 대화와 계획 문서 | **레포판 유지**. 외부 계획 체인은 Q1 |
| `codebase-explorer` | U-07, U-11, U-13, U-42 | 외부는 색인·훅 설치 | **레포판 유지** |
| `algorithm-*`, `benchmark`, `counterexample-hunter` | — | — | 유지(Q7 확장은 P5) |

### 3.3 U-40 ai-research 후보 (P4-T6, 2026-11-06)

- 확인 방법: `gh api`로 고정 커밋 `a25cf9ec00e2745d03f8704acf6f6919694ccd9a`의 `skills/` 목록(177개), 파일 트리, 후보 8개의 `SKILL.md` 앞부분을 읽었다. 내려받거나 복사한 것은 없다.
- 레포 루트는 MIT(`LICENSE.md`)인데, **스킬마다 frontmatter `license`가 다르다**(BSD-3-Clause, Apache-2.0 포함). 채택하면 스킬별 라이선스를 lock과 NOTICES에 따로 적어야 한다.
- 대부분 Python 3.10~3.12와 특정 패키지 버전을 요구한다. 키트(R-08)가 아니라 사용자 프로젝트의 요구사항이므로 설치를 막지는 않지만, 스킬이 `pip install`을 안내한다.
- 177개 중 대부분은 생물·화학·물리 분야 전용이다. ai-research 요구 기능(실험, 데이터셋 검증, 파이프라인, 재현성, 결과 비교)에 맞는 것만 골랐다.

| 스킬 | 라이선스 | 크기(파일/바이트) | 스크립트 | 비밀값·네트워크 | 판단 |
|---|---|---|---|---|---|
| `experimental-design` | MIT | 7 / 66,897 | 2 | 설치 때만 네트워크. 설명 1,014자(1,024 한도 근접) | **후보** |
| `statistical-analysis` | MIT | 7 / 120,509 | 1 | 설치 때만 | **후보** |
| `statistical-power` | MIT | 6 / 78,425 | 2 | 설치 때만 | **후보** |
| `scientific-critical-thinking` | MIT | 9 / 133,159 | 0 | 없음. 선택 기능(그림)만 `OPENROUTER_API_KEY` | **후보**(선택 기능은 쓰지 않음) |
| `exploratory-data-analysis` | MIT | 21 / 210,866 | 13 | 핵심 CLI는 로컬. 스크립트가 많음 → medium | **후보** |
| `scikit-learn` | BSD-3-Clause | 11 / 139,099 | 2 | 설치 때만 | **후보** |
| `pytorch-lightning` | Apache-2.0 | 11 / 81,105 | 3 | 선택 로거는 외부 서비스·자격 증명 | **후보** |
| `transformers` | Apache-2.0 | 7 / 80,649 | 0 | Hub 다운로드, 비공개 모델은 `HF_TOKEN` | **REFERENCE**. 토큰 안내가 25곳 |
| `shap`, `optimize-for-gpu`, `scientific-visualization`, `uncertainty-and-units` | — | 140~301 KB | 0~8 | — | **REFERENCE**. 필요할 때 `kit source add`(P4-T8) |
| 나머지 165개 | — | — | — | — | **REFERENCE**. 분야 전용 |

- 제안: 후보 7개를 새 팩 `research`로 묶어 vendor하고, `ai-research` 프로필의 `packs`에 넣는다(standard 정책 전용, restricted에는 넣지 않음). 실제 복사, lock 항목, 라이선스 기록, 키트 형식 검사는 **검토자 승인 후** 별도로 한다(P4-T3 게이트).

## 4. 채택안 설치 계획과 보안 영향 (§14.3 게이트)

모든 채택안에 공통으로 적용하는 것:
- 키트는 외부 파일을 **복사만** 하고 실행하지 않는다.
- 레포에 넣는 시점은 P4-T4이고 그때만 네트워크를 쓴다(GitHub API로 고정 커밋의 blob을 받음).
- 사용자가 `install`할 때는 네트워크를 쓰지 않는다. 레포 안의 사본을 쓴다.
- `sources.lock.json`에 기록하는 항목: 출처, 커밋, 경로, 라이선스, `content_sha256`, 위험.
- `third_party/<owner>-<repo>/`에 둘 것: LICENSE 원문, 받은 파일 그대로.
- `THIRD_PARTY_NOTICES.md`에 고지를 추가한다.
- `install`과 `verify`는 해시를 다시 확인한다.

| # | 무엇을 | 어디에(레포 → 설치 대상) | 누가 받나 | 권한·실행 | 네트워크 | 보안 영향 |
|---|---|---|---|---|---|---|
| A1 | superpowers 스킬 5개(파일 12개) | `third_party/obra-superpowers/skills/<n>/` → `.agents/skills/<n>/`(Codex), `.claude/skills/<n>/`(Claude) | standard 정책, 두 에이전트, `core` 팩 | 없음. `find-polluter.sh`, `condition-based-waiting-example.ts`는 참고 파일이고 키트가 실행하지 않음 | 없음 | low. 문서 안에 `superpowers:<이름>` 표기가 남지만 키트 설치 이름과 같아서 해석됨(Q3) |
| A2 | `frontend-design`(SKILL.md + LICENSE.txt) | `third_party/anthropics-skills/skills/frontend-design/` → 두 에이전트 스킬 폴더 | standard, web/fullstack 팩 | 없음 | 없음 | low. 스킬 폴더 안 LICENSE.txt를 함께 설치함(Apache §4 고지) |
| A3 | `emil-design-eng`(SKILL.md 1개) | `third_party/emilkowalski-skills/skills/emil-design-eng/` → 두 에이전트 | standard, web/fullstack | 없음 | 없음 | low. 677줄이라 500줄 경고가 남음(정보만) |
| A4 | `web-design-guidelines`: 키트가 쓴 SKILL.md + `references/command.md`(고정 사본 8,055 B) | SKILL.md `shared/skills/web-design-guidelines/`, 원문 `third_party/vercel-labs-web-interface-guidelines/` → 두 에이전트 | standard, web/fullstack | 없음 | **사용할 때도 없음**(원본과 달리 원격 규칙을 받지 않음) | low. 규칙이 바뀌면 `kit source update`로 갱신(P4-T8) |
| A5 | OMX 스킬 29개(파일 30개) + prompts 32개(마크다운) | `user/codex/omx/`(P4-T7) → `install --scope user`일 때만 `~/.codex/skills/`, `~/.codex/prompts/` | 사용자 범위, Codex만. 프로젝트 설치에는 들어가지 않음 | 없음. **npm CLI `oh-my-codex@0.21.46`은 키트가 설치하지 않음**. `postinstall`이 있어서 사람이 실행할 수동 명령으로만 출력 | 없음 | 파일은 low. 전역 쓰기는 R-06에 따라 opt-in 확인 후에만. 이 PC 사본(OMX 스킬 28개, prompts 37개)과 태그 사본(29개, 32개)이 다르므로 P4-T7에서 diff를 보고함 |
| R1 | `@playwright/mcp@0.0.84` 카탈로그 항목(설정만) | `mcp/manifest.json` 또는 P4-T5 카탈로그 → `.codex/config.toml` 블록, `.mcp.json` 키 | web/fullstack, **기본 비활성**, `--mcp playwright`로 opt-in | MCP가 브라우저를 실행하고 지정한 URL을 엶 | 첫 실행 때 npm과 브라우저 바이너리를 받음. 사용 중 외부 사이트 접속 | medium. 버전 고정, stdio. `plan`에 "would use network"로 표시(D-14) |

채택안이 승인되면 바뀌는 것(P4-T4 이후):
- `catalog/skills.json`에 항목을 추가한다(origin `source:<id>`, `replaces`, `policies`).
- 레포판 `systematic-debugging`, `tdd-automator`, `submission-validator`는 restricted 전용이 된다.
- 기존 경로의 바이트는 그대로다(골든 테스트, V-22).

## 5. P4-T4로 넘기는 구현 사항 (평가 중 발견)

### 5.1 키트 형식 검사 결과 (실제 실행, `kit_rules=False`, 두 에이전트)

| 스킬 | 오류 | 경고 |
|---|---|---|
| A1 5개, `brainstorming`, `writing-plans`, `using-git-worktrees`, `finishing-a-development-branch` | 0 | 0 |
| `frontend-design`, `karpathy-guidelines` | 0 | 0 |
| `emil-design-eng` | 0 | "SKILL.md is longer than 500 lines" |
| `executing-plans`, `subagent-driven-development` | **1**: `../requesting-code-review/code-reviewer.md` 링크가 스킬 밖을 가리킴 | 0 |
| `caveman` | **1**: 여러 줄 `description:`을 키트 파서가 읽지 못함 | — |

### 5.2 해야 할 일
1. **형제 스킬 링크.** 계획 체인을 채택하면(Q1) 고칠 방법이 둘이다.
   - (a) `../<다른 스킬>/` 링크를 "같은 설치 묶음 안에 있으면 허용"으로 바꾼다.
   - (b) 링크 대상 파일을 복사해 넣는다(adapted).
   - 사양상 스킬은 자기 폴더 안을 가리키는 것이 원칙이므로 (b)를 권장한다.
2. **YAML 여러 줄 스칼라(`>`, `|`).** 이 형식은 사양상 유효하다. 지금 채택안에는 없지만 `kit source add`(P4-T8)가 받을 수 있으므로 파서에 추가해야 한다.
3. **라이선스 파일 위치.** 스킬 폴더 안 `LICENSE.txt`(A2)는 설치본에도 함께 둔다. 저장소 루트 LICENSE(A1, A3, A4, A5)는 `third_party/<id>/LICENSE`와 NOTICES로 처리한다.
4. **해시.** `content_sha256`은 파일별로 둔다. P4-T4 테스트는 `third_party` 사본이 lock 해시와 같은지 확인한다.

## 6. 이 PC의 전역 항목 (REQ-SRC-008)

이 PC에서 이름과 버전만 읽었다. 내용과 설정값은 읽지 않았다.

| 위치 | 항목 | 출처 판정 | 결정 |
|---|---|---|---|
| `~/.codex/skills/` | 스킬 30개. OMX 계열 28개 + `superpowers` + `prometheus-strict` | OMX 28개는 모두 태그 사본(29개)에 있음. 태그에만 있는 것은 `git-master` 1개. prompts는 PC 37개, 태그 32개(차이는 P4-T7 diff). `superpowers`는 U-49 | OMX → A5. superpowers → A1과 같은 출처 |
| `~/.codex/skills/prometheus-strict` | 1개 | **출처를 모름**(OMX 태그 사본에 없음) | **DEFER**. P4-T7 `capture`에서 내용을 보고 출처를 확인한 뒤 결정(Q4) |
| P4-T7 capture 결과(2026-11-06, 읽기 전용 dry-run) | OMX 스킬 28개·prompts 32개 | 모두 `omx (differs from v0.21.46)`. PC 사본은 description 앞에 `[OMX]`가 붙고 내용이 태그보다 오래됨 | 이 PC에서 `install --scope user`를 하면 OMX가 CONFLICT(PARTIAL)로 보고되고 PC 파일은 그대로 남는다. 태그 사본으로 바꾸려면 사람이 PC 사본을 먼저 치워야 한다 |
| 같은 결과 | `prometheus-strict` 스킬, prompts `prometheus-strict-*`, `scholastic`, `sisyphus-lite` | `[OMX]` 접두어는 있으나 태그에 없음 → `unknown origin (not carried)` | Q4는 여전히 열림. 저장소로 가져오지 않는다 |
| Q4 출처 확인(2026-11-06, 검토자 요청 "내용 확인 후 결정") | 같은 6개 파일 | **OMX 자신의 파일(MIT)**. `Yeachan-Heo/oh-my-codex`에 있었고 커밋 `b6b9141eb678`(2026-08-12, "remove deprecated skill shims and prometheus-strict")에서 삭제됨. 그래서 v0.21.46 태그에 없다. 스킬 README는 OMO Prometheus(`code-yeongyu/oh-my-openagent`)의 개념만 따온 clean-room 구현이라고 밝힘 | **PC 사본을 내 것으로 포함**(검토자 결정 2026-11-06). capture 허용 목록 `codex.copy` → `user/codex/own/`(7개 파일, PC와 바이트 동일). 라이선스는 OMX MIT(`third_party/Yeachan-Heo-oh-my-codex/LICENSE`), NOTICES에 기록 |
| OMX 사본 차이 | OMX 스킬 28개·prompts 32개 | 위와 같음 | **그대로 둠**(검토자 결정 2026-11-06). user 범위 설치는 계속 CONFLICT(PARTIAL)이고 PC 파일은 바꾸지 않는다 |
| 같은 결과 | `~/.codex/agents/*.toml` 22개 | `generated by omx setup (not carried)` | 가져오지 않는다 |
| `~/.claude/plugins` | `superpowers@superpowers-marketplace` 6.2.0(`44c9b2d6e889`) | U-49 | user 범위 플러그인 참조로 기록(P4-T7). 프로젝트 범위는 A1 스킬 사본을 씀 |

## 7. 검토자 질문

- **Q1 superpowers 계획 체인을 넣을까?** 대상은 6개다: `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`.
  - 서로를 참조하므로 묶음으로만 넣을 수 있다.
  - 위험 요소:
    - `brainstorming`이 127.0.0.1에 로컬 서버를 띄운다(medium).
    - `executing-plans`가 bash 스크립트를 쓴다.
    - git worktree와 브랜치를 만든다.
  - **권장:** 지금은 DEFER하고 `task-router`를 유지한다. 원하시면 standard 정책의 opt-in 팩 `workflow`로 넣는다(형제 링크 처리 §5.2-1 포함).
- **Q2 karpathy 지침(U-16/U-32)을 복사할까?** README와 frontmatter에 "MIT"만 적혀 있고 저작권 표시가 없어 MIT 고지 문구를 정확히 만들 수 없다.
  - **권장:** REFERENCE. 내용 대부분이 이미 standard 정책에 있다.
- **Q3 A1 스킬 본문의 `superpowers:<이름>` 표기를 그대로 둘까?**
  - **권장:** verbatim으로 둔다. 키트 설치 이름과 뒷부분이 같아서 에이전트가 찾을 수 있다. 바꾸면 "adapted"가 되어 갱신할 때마다 diff 관리가 필요하다.
- **Q4 `prometheus-strict`(출처 모름)는 P4-T7에서 내용을 확인한 뒤 결정해도 될까?**

## 8. 검토자 결정 (2026-11-06)

| 질문 | 결정 | 반영 |
|---|---|---|
| 채택안 | A1~A5, R1 승인 | P4-T4(A1~A4, A6, A7), P4-T5(R1), P4-T7(A5) |
| Q1 | **계획 체인 6개를 opt-in 팩 `workflow`로 넣는다**(A7) | `profiles/packs/workflow.json`, standard 정책만. `--profile core,workflow`일 때만 설치. 형제 스킬 링크는 처음에 (b) 복사로 정했으나 P4-T4에서 **(a)로 바꿨다**: `executing-plans/scripts/task-start`가 `../../subagent-driven-development/scripts/task-brief`를 실행하는 등 스크립트도 형제 폴더에 기대므로 파일 하나 복사로는 고쳐지지 않는다. 파일은 원문 그대로 두고, 카탈로그 `requires`로 함께 설치를 강제하며 검사기는 그 형제 스킬의 파일을 가리키는 링크만 허용한다. `task-router`는 그대로 core에 남는다 |
| Q2 | **고지를 달고 복사한다**(A6) | `karpathy-guidelines` 스킬을 `multica-ai/andrej-karpathy-skills@2c606141936f1eeef17fa3043a72095b4765b9c2`에서 복사. NOTICES에 "README와 frontmatter가 MIT라고 밝힘, 저작권 표시 없음, 저장소 기여자에게 귀속"이라고 적는다. standard 정책, 두 에이전트, core 팩 |
| Q3 | `superpowers:<이름>` 표기를 그대로 둔다 | verbatim |
| Q4 | `prometheus-strict`는 P4-T7에서 확인 | — |

추가 채택안의 설치 계획과 보안 영향:

| # | 무엇을 | 어디에 | 누가 받나 | 권한·실행 | 네트워크 | 보안 영향 |
|---|---|---|---|---|---|---|
| A6 | `karpathy-guidelines`(SKILL.md 1개, 68줄) | `third_party/multica-ai-andrej-karpathy-skills/skills/karpathy-guidelines/` → 두 에이전트 스킬 폴더 | standard, core | 없음 | 없음 | low. 라이선스 근거가 README 표기뿐이라는 점을 NOTICES와 lock에 남김 |
| A7 | superpowers 계획 체인 6개 | `third_party/obra-superpowers/skills/<n>/` → 두 에이전트 스킬 폴더 | standard, `workflow` 팩(opt-in) | 에이전트가 판단해 실행할 수 있는 것: `brainstorming/scripts/start-server.sh`(Node 로컬 서버, 기본 127.0.0.1), `executing-plans/scripts/task-*`(bash, git), git worktree·브랜치 생성. 키트는 실행하지 않음 | 키트는 없음. 로컬 서버는 루프백만 | medium. 팩 설명과 `plan` 출력에 위 실행 가능성을 적음 |

### 8.1 3단계: MCP·플러그인·수동 도구 반영 (2026-11-08, 검토자 승인)

- 확인 방법: 2026-11-08 조사 노트와, 고정 커밋의 파일을 `raw.githubusercontent.com`에서 읽어 확인(플러그인 4개의 `.claude-plugin/plugin.json`, LICENSE, `markitdown-mcp`의 `__about__.py`, `rea-agents`의 `package.json`, 각 도구 README). 원격 MCP 주소는 각 서비스의 공식 문서 페이지에서 확인했다. 아무것도 clone, 설치, 실행하지 않았다.
- 키트는 항목을 기록하고 명령을 출력할 뿐이다. 위험도 high이거나 API 키가 필요한 항목은 모두 기본 꺼짐이다(`kit/mcp_catalog.py`가 강제). 키는 환경 변수 **이름만** 적는다(§15).
- 원격 MCP는 `catalog/mcp.json`에 넣지 않는다(stdio만, §15). `catalog/manual.json`에 사람이 직접 실행할 `claude mcp add --transport http <name> <url>`과 OAuth 로그인만 적고, 토큰이나 헤더 값은 적지 않는다.

**어디에 들어갔나**

| 이름 | 카탈로그 | 위험 | 기본 | lock 커밋 | 환경 변수 | U-ID |
|---|---|---|---|---|---|---|
| `codebase-memory` | `catalog/mcp.json`(`uvx codebase-memory-mcp==0.12.1`) | medium | 꺼짐 | `a7158ac2f48c` | — | U-13 |
| `markitdown` | `catalog/mcp.json`(`uvx markitdown-mcp==0.0.1a8`) | high | 꺼짐 | `21d9c1d01ecc` | — | U-43 |
| `inspo` | `catalog/mcp.json`(`npx -y inspo-mcp@0.2.0`) | medium | 꺼짐 | `022f80977c1e` | `TOGETHER_API_KEY`(선택) | U-39 |
| `rea` | `catalog/mcp.json`(`npx -y rea-agents@6.8.0 mcp`) | high | 꺼짐 | `160d821ac9a0` | — | U-34 |
| `scrapling` | `catalog/mcp.json`(목록만, 명령 없음) | high | 꺼짐 | — | — | U-47 |
| `filetree` | `catalog/plugins.json`(url) | medium | 꺼짐 | `a3d36b1a56c0` | — | U-28 |
| `replay-theater` | `catalog/plugins.json`(git-subdir) | medium | 꺼짐 | `569c5283d9a0` | — | U-29 |
| `savvy-progress` | `catalog/plugins.json`(git-subdir) | medium | 꺼짐 | `c871c153ead5` | — | U-27 |
| `effortless` | `catalog/plugins.json`(url) | high | 꺼짐 | `7912a6ccdf0a` | `TYPESAFE_API_KEY`(선택) | U-09 |
| `headroom` | `catalog/manual.json` 0.43.1 | high | — | `2d3ee5184643` | 끄기용 `HEADROOM_TELEMETRY` 등 | U-08 |
| `rtk` | `catalog/manual.json` rtk-oss 1.1.0 | high | — | `753a3b0e939f` | — | U-20 |
| `graphify` | `catalog/manual.json` graphifyy 0.9.104 | high | — | `433a57a00290` | — | U-07 |
| `claude-mem` | `catalog/manual.json` 15.12.0 | high | — | `eb00299a6a74` | `CLAUDE_MEM_ONLINE_OPTIN` | U-42 |
| `openrig` | `catalog/manual.json` 0.7.9 | high | — | `ddb9d25be74a` | — | U-10 |
| `ruflo` | `catalog/manual.json` 3.72.2 | high | — | `b7bc909d5f0d` | — | U-44 |
| `bureau-des-agents` | `catalog/manual.json` 0.1.0 | medium | — | `184daa898cbb` | — | U-45 |
| `mobbin` | `catalog/manual.json`(원격 MCP 안내) | high | — | — | —(OAuth) | U-35 |
| `nicelydone` | `catalog/manual.json`(원격 MCP 안내) | high | — | — | —(OAuth) | U-36 |
| `refero` | `catalog/manual.json`(원격 MCP 안내) | high | — | — | —(OAuth) | U-37 |
| `claude-code-router` | `catalog/manual.json` 3.1.3(그대로) | high | — | `057abaa1f955` | — | U-23 |
| `security-guidance` | `catalog/plugins.json`(고정 그대로, 2.0.17) | high | 꺼짐 | `ff920a4094a3` | `ANTHROPIC_API_KEY`(선택) | U-46 |

**넣지 않은 것**

| 항목 | 결정 | 이유 |
|---|---|---|
| U-19 context-mode(ELv2) | 링크만 | ELv2는 OSI 오픈소스가 아니다. 키트 라이선스 표(MIT, Apache-2.0, BSD-2/3, ISC, 0BSD, CC-BY-4.0, Unlicense)에 없고 `other`는 `--accept-license`로만 복사한다. 플러그인 항목은 사용자 PC 설치까지 이어지므로 같은 기준으로 플러그인 카탈로그에 넣지 않았다. 참고: `mksglu/context-mode` v2.1.6, 경로 `plugins/claude-code`, 커밋 `e7b84d916570`(조사 노트, 확인하지 않음) |
| U-38 Lazyweb | DEFER | 공식 문서에서 MCP 엔드포인트와 인증 방식을 확인하지 못했다(UNVERIFIED). `lazyweb.com`은 다른 서비스로 보인다. 확인되면 manual.json에 추가 |

**이전 REJECT 유지와 대안**

| 항목 | 이유(2026-11-08 다시 확인) | 대안 |
|---|---|---|
| U-11 graft(`@nanonets/graft`) | `postinstall`이 분리된 프로세스로 텔레메트리를 보냄, PostHog 키가 배포본에 들어 있음, npm 0.29.0이 태그와 맞지 않음 | 코드 색인은 `codebase-memory`(U-13, 기본 꺼짐) 또는 레포 `codebase-explorer` |
| U-18 mods | 2026-03-09 보관(archived). 후속은 Crush. 설치가 winget/brew/go | 필요하면 후속 프로젝트(Crush)를 따로 평가 |
| U-21 find-skills | `npx skills add ... -g -y`가 전역·버전 고정 없이 설치하고 텔레메트리가 기본 켜짐 | 키트의 `kit source add`(고정 커밋, 검사, 승인) |
| U-26 | 라이선스 없음. 제외 유지 | — |

**문서 전용 링크**(설치 대상 아님)

| 항목 | 링크 | 고정 | 메모 |
|---|---|---|---|
| U-25 harness2 | https://github.com/google-research/harness2 | HEAD `686881751887` | Linux 전용 |
| U-14 OpenMontage | https://github.com/OpenMontageInc/OpenMontage | — | AGPL-3.0. 이전 주소 `calesthio/OpenMontage` |
| U-15 prompts.chat | https://github.com/f/prompts.chat | `ba34d09010de` | 코드 MIT, 프롬프트 CC0 |
| U-24 Second-Brain | https://github.com/KasperZutterman/Second-Brain | `4302f25c60f5` | 링크 모음 |

**UNVERIFIED로 남긴 것**

- 모든 새 MCP·플러그인의 실제 실행 동작(키트는 실행하지 않음). 특히 `uvx codebase-memory-mcp==0.12.1`과 `npx -y inspo-mcp@0.2.0`이 인자 없이 stdio 서버로 뜨는지.
- `TOGETHER_API_KEY` 발급 페이지(README에 없음. 카탈로그는 저장소 README를 가리킴).
- Nicelydone의 Claude Code 명령 문구(로그인 뒤에만 보임. 카탈로그는 Claude Code 일반 형식을 씀).
- rtk 훅 제거 플래그(Quick Start 문서를 가리킴), claude-mem·openrig·ruflo의 완전한 제거 절차(상류 문서가 일부뿐이라고 항목에 적음).
- inspo-mcp 0.2.0 의존성의 설치 스크립트.

**secret 스캐너 통일**(같은 날): `kit source add`의 스캔(`kit/source_scan.py`)이 `kit capture`와 같은 규칙(`kit/secrets_scan.py` `LITERAL_PATTERNS`)을 쓴다. 비밀 이름 옆의 실제 값과 `Authorization: Bearer <값>`은 REVIEW(사람 확인, `--accept-risk`), `<your-token>`·`eyJhbGciOi...` 같은 자리표시자는 WARN이다. 토큰 형식(sk-, ghp_ 등)은 그대로 BLOCK.

## 9. `kit source` 기록

`kit source`가 남기는 기록이다(P4-T8, ADR-021).

2026-11-08 추가(검토자 승인, 조건: "너무 위험한 것은 뺀다"): 다섯 팩은 모두 opt-in이고 standard 정책 전용이다. 기본 팩과 기존 프로필에는 넣지 않았고 restricted에는 들어가지 않는다. 스킬마다 SKILL.md와 함께 들어가는 파일을 읽고 위험 기준(원격 스크립트·전역 설치, 전역 설정 수정, 외부 전송·토큰 파일 저장, 숨은 유니코드·인젝션, 확인 없는 파괴·배포, 빠진 스크립트 의존)으로 걸렀다. 뺀 스킬과 이유는 §3의 U-04, U-06, U-17, U-22, U-31, U-33 행에 있다. `--accept-risk`는 `emilkowalski-skills`에만 썼고, `--accept-license`와 `--include`는 쓰지 않았다. `cloudflare-skills`는 처음 14개로 넣은 뒤 `basin`을 빼기 위해 `source remove`하고 13개로 다시 넣었다(아래 remove·add 줄).

| 날짜 | 동작 | id | 출처@커밋 | 라이선스 | 반영 | 팩 | 겹침 |
|---|---|---|---|---|---|---|---|
| 2026-11-06 | add | `k-dense-ai-scientific-agent-skills` | K-Dense-AI/scientific-agent-skills@a25cf9ec00e2 | MIT | vendored-verbatim | research | — |
| 2026-11-08 | add | `cloudflare-skills` | cloudflare/skills@6eb6c781aa9b | Apache-2.0 | vendored-verbatim | cloudflare | — |
| 2026-11-08 | add | `emilkowalski-skills` | emilkowalski/skills@c8a79627b59d | MIT | vendored-verbatim | motion | — |
| 2026-11-08 | add | `mattpocock-skills` | mattpocock/skills@4ae2317ddb22 | MIT | vendored-verbatim | planning-extras | — |
| 2026-11-08 | add | `dietrichgebert-ponytail` | DietrichGebert/ponytail@96608e078b2d | MIT | vendored-verbatim | lean | — |
| 2026-11-08 | add | `affaan-m-ecc` | affaan-m/ECC@d2ef2680594f | MIT | vendored-verbatim | eng-patterns | — |
| 2026-11-08 | remove | `cloudflare-skills` | cloudflare/skills@6eb6c781aa9b | Apache-2.0 | vendored-verbatim | cloudflare | — |
| 2026-11-08 | add | `cloudflare-skills` | cloudflare/skills@6eb6c781aa9b | Apache-2.0 | vendored-verbatim | cloudflare | — |
