# 08 사용자 목록 출처 확정표 (REQ-SRC-006)

- 입력: `docs/v2/inputs/user-source-list.txt`. 항목은 49개다(원본 번호가 29 다음에 20부터 다시 시작한다).
- 2차본(2026-11-05): 검토자 지시("깃허브에서 이름 그대로 찾아라")에 따라 1차본의 UNRESOLVED 11개를 GitHub에서 이름 그대로 검색해 정했다. 모든 후보 저장소가 실제로 있는지도 `gh repo view`로 확인했다.
- 확인 방법: `gh search repos "<이름> in:name"`(별 수 정렬)과 `gh repo view <저장소> --json nameWithOwner,stargazerCount,licenseInfo,pushedAt,isArchived`. 실행일은 2026-11-05다.
  - 라이선스 열은 GitHub가 감지한 SPDX 키다. `-`는 GitHub가 라이선스를 감지하지 못했다는 뜻이다.
  - **채택 전에 저장소의 LICENSE 원문과 고정 커밋을 다시 확인한다**(원문 P4-T3/P4-T4).
- 이름 바뀜: `gh repo view`가 이전 이름을 새 저장소로 넘겨준 경우다. 표에는 현재 이름을 적었다.
- 확신도: `HIGH`는 이름과 용도가 모두 맞는 경우, `MED`는 이름은 맞지만 다른 후보가 있는 경우다. UNRESOLVED는 0개다.

| ID | 원문 | 저장소(현재 이름) | ★ | 라이선스 | 최근 push | 종류 | 확신도 | 메모 |
|---|---|---|---|---|---|---|---|---|
| U-01 | frontend-design | `anthropics/skills` 안 `frontend-design`(같은 이름의 플러그인이 `anthropics/claude-plugins-official`에도 있음) | 187,622 | `-`(스킬마다 다름) | 2026-10-28 | skill | MED | U-31에 포함. 스킬별 라이선스 확인 |
| U-02 | ui-ux-pro-max | `nextlevelbuilder/ui-ux-pro-max-skill` | 145,517 | MIT | 2026-11-05 | skill | HIGH | 디자인 묶음 |
| U-03 | hallmark | `Nutlope/hallmark` | 48,450 | MIT | 2026-11-05 | skill | HIGH | 디자인 묶음. 프로젝트별 로그 파일을 씀 |
| U-04 | emil-design-eng | `emilkowalski/skills` 안 `emil-design-eng` | 53,719 | MIT | 2026-11-04 | skill | HIGH | SKILL.md가 약 680줄로 보고됨(Claude 권장 500줄 초과) |
| U-05 | web-design-guidenlines | `vercel-labs/agent-skills` 안 `web-design-guidelines` | 33,574 | **`-`** | 2026-10-28 | skill | MED | **라이선스를 감지하지 못함 → 포함 전에 확인 필수** |
| U-06 | ponytail | `DietrichGebert/ponytail` | 184,941 | MIT | 2026-10-29 | plugin | HIGH | 코드량 절약 묶음 |
| U-07 | graphify | `Graphify-Labs/graphify`(이전 이름 `safishamsi/graphify`) | 142,745 | Apache-2.0 | 2026-11-03 | tool+skill+hook | HIGH | `CLAUDE.md` 수정과 PreToolUse 훅 설치 → 고위험. 코드 인덱싱 묶음 |
| U-08 | headroom | `headroomlabs-ai/headroom` | 78,905 | Apache-2.0 | 2026-11-05 | tool(프록시)+mcp | HIGH | 로컬 프록시가 요청을 중계 → 고위험. 컨텍스트 절약 묶음 |
| U-09 | effortless | `HeyCubit/effortless` | 325 | MIT | 2026-10-23 | mod | HIGH | 모델 라우팅 묶음 |
| U-10 | openRig | `mvschwarz/openrig` | 8,650 | Apache-2.0 | 2026-11-05 | tool | HIGH | tmux 기반. Windows 지원 확인 필요 |
| U-11 | graft | `trailhq/Trail-Code`(이전 이름 `trailhq/Graft`, npm `@nanonets/graft`) | 11,115 | MIT | 2026-11-06 | tool+hook | HIGH | **검토자 확인(2026-11-06)**: 두 후보 중 별이 많은 쪽(`AEndrix03/Graft` 64★). 코드 인덱싱 묶음 |
| U-12 | agency agents | `msitarzewski/agency-agents` | 166,677 | MIT | 2026-10-25 | collection | HIGH | 오케스트레이션 묶음 |
| U-13 | codebase Memory MCP | `DeusData/codebase-memory-mcp` | 48,154 | MIT | 2026-11-04 | mcp | HIGH | 코드 인덱싱 묶음 |
| U-14 | openMontage | `calesthio/OpenMontage` | 76,921 | **AGPL-3.0** | 2026-11-03 | collection | HIGH | 레포에 포함 불가, 참조만 |
| U-15 | prompts.chat | `f/prompts.chat` | 175,872 | other | 2026-11-05 | collection | HIGH | 라이선스 원문 확인 필요 |
| U-16 | 카파시 CLAUDE.md | `multica-ai/andrej-karpathy-skills`(이전 이름 `forrestchang/…`) 안 `CLAUDE.md` | 229,724 | **`-`** | 2026-04-20 | doc | HIGH | U-32와 같은 저장소. **라이선스를 감지하지 못함** |
| U-17 | 클라우드플레어 | `cloudflare/skills` | 3,283 | Apache-2.0 | 2026-11-03 | skill | MED | 다른 후보는 `cloudflare/mcp-server-cloudflare`(4,447★, 원격 MCP). 목록 성격(스킬)에 맞춰 skills를 고름 |
| U-18 | mods | `charmbracelet/mods` | 4,520 | MIT | 2026-03-09 | tool(CLI) | HIGH | **검토자 확인(2026-11-06)**: 두 후보 중 별이 많은 쪽(`karanb192/awesome-claude-code-mods` 880★). **보관(archived)된 저장소** |
| U-19 | context-mode | `mksglu/context-mode` | 33,535 | other | 2026-11-05 | mcp/plugin | HIGH | 컨텍스트 절약 묶음. 라이선스 원문 확인 필요 |
| U-20 | RTK | `rtk-ai/rtk` | 85,622 | Apache-2.0 | 2026-11-05 | tool+hook | HIGH | 컨텍스트 절약 묶음. 셸 훅 |
| U-21 | find-skills | `vercel-labs/skills` 안 `find-skills` | 38,214 | MIT | 2026-11-05 | skill | HIGH | 외부 설치를 유도하므로 출처 관리와 충돌할 수 있음 |
| U-22 | ECC | `affaan-m/ECC`(이전 이름 `affaan-m/everything-claude-code`) | 297,597 | MIT | 2026-11-02 | collection | HIGH | 레포 스킬과 광범위하게 겹침 → 골라서 채택 |
| U-23 | ROUTER | `musistudio/claude-code-router`(npm `@musistudio/claude-code-router`, bin `ccr`) | 38,016 | MIT | 2026-10-10 | tool(proxy) | HIGH | **검토자 확인(2026-11-06)**: 검토자가 이 저장소를 뜻했다고 확인. 1·2차본은 `weave-os/router`(5,615★)로 잘못 골랐다. 모델 라우팅 묶음 |
| U-24 | 세컨드브레인 | `KasperZutterman/Second-Brain` | 1,861 | MIT | 2026-10-14 | index(링크 모음) | HIGH | **검토자 확인(2026-11-06)**: 두 후보 중 별이 많은 쪽(`NicholasSpisak/second-brain` 771★, 라이선스 없음). 공개 Zettelkasten·Second Brain 링크 모음이라 설치 대상이 아님. 참고: 이름 검색 1위는 `eugeniughelbur/obsidian-second-brain`(5,189★)이지만 검토자 기준(두 후보)에 따라 고르지 않음 |
| U-25 | 구글 하네스2 | `google-research/harness2` | 22,775 | Apache-2.0 | 2026-11-02 | tool(하네스 최적화) | HIGH | |
| U-26 | claude code projects | **제외** | — | — | — | — | — | **검토자 확인(2026-11-06)**: 검토자가 제외함. 1·2차본 후보는 `danielrosehill/Claude-Code-Projects-Index`(578★, 라이선스 없음) |
| U-27 | Savvy progress | `JohnnyVizz/claude-kit` 안 `savvy-progress` | 349 | MIT | 2026-10-12 | mod | HIGH | |
| U-28 | File Tree | `data-goblin/claude-code-filetree` | 373 | MIT | 2026-11-05 | mod | HIGH | Claude Code 2.1.287 이상 필요 |
| U-29 | repaly theater | `anthropics/claude-code-playground` 안 `claude-code/mods/replay-theater` | 339 | Apache-2.0 | 2026-10-14 | mod | MED | 폴더 경로는 2차 출처 기준이라 P4-T3에서 확인 |
| U-30 | Caveman | `JuliusBrussee/caveman` | 117,664 | Apache-2.0 | 2026-11-05 | skill | HIGH | 컨텍스트 절약 묶음 |
| U-31 | Anthropic skills | `anthropics/skills` | 187,622 | `-`(스킬마다 다름) | 2026-10-28 | collection | HIGH | |
| U-32 | karpathy skills | `multica-ai/andrej-karpathy-skills` | 229,724 | **`-`** | 2026-04-20 | skill/doc | HIGH | U-16과 합침 |
| U-33 | matt pocock skills | `mattpocock/skills` | 314,363 | MIT | 2026-11-05 | collection | HIGH | |
| U-34 | REA | `morluto/rea` | 433,046 | MIT | 2026-11-05 | tool+skill+mcp | HIGH | 사용자 홈에 자동 설치 → 고위험 |
| U-35 | mobbin mcp | Mobbin 공식 MCP(원격, 유료) | — | 서비스 약관 | — | mcp(원격) | MED | 디자인 레퍼런스 MCP 묶음. 원격 MCP라 기본 비활성 |
| U-36 | nicelydone mcp | Nicelydone 공식 MCP(원격, OAuth) | — | 서비스 약관 | — | mcp(원격) | MED | 디자인 레퍼런스 MCP 묶음 |
| U-37 | refero mcp | Refero 공식 MCP(원격, 유료) | — | 서비스 약관 | — | mcp(원격) | MED | 디자인 레퍼런스 MCP 묶음 |
| U-38 | lazyweb mcp | Lazyweb MCP(원격, 토큰 필요) | — | 서비스 약관 | — | mcp(원격) | MED | 디자인 레퍼런스 MCP 묶음 |
| U-39 | inspoai mcp | `Nutlope/inspo` | 974 | MIT | 2026-10-28 | mcp(stdio/HTTP) | MED | 이름이 정확히 `inspo`인 저장소 중 1위. InspoAI 공식 커넥터(`io.inspoai.app`, OAuth)도 있음 |
| U-40 | scientific-agnet-skills | `K-Dense-AI/scientific-agent-skills`(이전 이름 `claude-scientific-skills`) | 56,186 | MIT | 2026-11-02 | collection | HIGH | ai-research 프로필 후보 |
| U-41 | anatomy | `wheresryan22/anatomy` | 25,121 | MIT | 2026-10-18 | skill | HIGH | "실제 기계를 아이소메트릭 일러스트로 그리는 에이전트 스킬". 이름이 정확히 `anatomy`인 저장소 중 1위 |
| U-42 | thdotmack/claude-mem | `thedotmack/claude-mem` | 113,307 | Apache-2.0 | 2026-11-05 | plugin+hook | HIGH | 세션 기록을 로컬에 저장 → 중위험 |
| U-43 | markitdown | `microsoft/markitdown` | 193,985 | MIT | 2026-10-28 | tool/mcp | HIGH | |
| U-44 | Ruflo | `ruvnet/ruflo` | 80,956 | MIT | 2026-11-05 | tool | HIGH | 오케스트레이션 묶음. 고위험 |
| U-45 | le bureau des agents | `devlikemasta/bureau-des-agents` | 60 | MIT | 2026-10-14 | app | HIGH | 로컬 웹 서버 |
| U-46 | security-guidance | `anthropics/claude-plugins-official` 안 `security-guidance` | 46,196 | Apache-2.0 | 2026-11-05 | plugin(hook) | MED | 정확한 폴더는 P4-T3에서 확인 |
| U-47 | Scrapling | `D4Vinci/Scrapling` | 97,458 | BSD-3-Clause | 2026-11-04 | tool/mcp | HIGH | 네트워크 송신 → 고위험 |
| U-48 | knowledge-work-plugins | `anthropics/knowledge-work-plugins` | 34,812 | Apache-2.0 | 2026-11-04 | collection | HIGH | |
| U-49 | superpowers | `obra/superpowers` | 312,774 | MIT | 2026-11-03 | plugin/collection | HIGH | 이 PC에 설치된 커밋은 `44c9b2d6e889982ac18c27d05a19fefe335194e1`이다 |

목록에 없지만 함께 다루는 항목:
- `U-50` `launch-compliance-check`: `개발 시 주의사항` 20개 항목으로 새로 만드는 스킬이다(REQ-SKILL-001).
- `U-51` OMX: `Yeachan-Heo/oh-my-codex`(33,717★, MIT, push 2026-11-03). 이 PC의 Codex 전역 스킬 28개, `agents` 22개, `prompts` 37개의 출처다. 검토자 결정 Q6에 따라 레포에 포함한다(REQ-USER-005).

## 요약

- 확신도: HIGH 34, MED 15(그중 1개는 "낮음"), UNRESOLVED 0. 합계 49이고 스크립트로 셌다.
- 검토자 확인 후(2026-11-06): HIGH 38(U-11, U-18, U-23, U-24 추가), MED 10, 제외 1(U-26), UNRESOLVED 0. 합계 49. 바뀐 저장소는 U-23, U-24다.
- **라이선스를 감지하지 못한 저장소**(포함 전에 LICENSE 원문 확인 필수): U-05, U-16/U-32. U-01/U-31은 스킬마다 다르다. (U-24는 새 저장소가 MIT, U-26은 제외)
- **라이선스 원문을 확인해야 하는 저장소**(`other`): U-15, U-19
- **레포에 포함할 수 없는 저장소**: U-14(AGPL-3.0)
- **보관된 저장소**: U-18
- **원격 MCP**(기본 비활성, opt-in만): U-35~U-38. U-39는 공식 커넥터를 고를 때만 해당한다.
- **사용자 설정이나 요청 경로를 자동으로 바꾸는 도구**(고위험, 자동 활성화 금지): U-07, U-08, U-11, U-20, U-23, U-34, U-42, U-44

## 기능이 겹치는 묶음 (REQ-SRC-005, P4-T3에서 묶음마다 비교)

| 묶음 | 항목 |
|---|---|
| 디자인 스킬 | U-01, U-02, U-03, U-04, U-05 |
| 디자인 레퍼런스 MCP | U-35, U-36, U-37, U-38, U-39 |
| 컨텍스트·토큰 절약 | U-08, U-19, U-20, U-30, (U-06) |
| 코드 인덱싱·메모리 | U-07, U-11, U-13, U-42 |
| 오케스트레이션·멀티 에이전트 | U-10, U-12, U-22, U-44, U-45, U-51(OMX) |
| 모델 라우팅 | U-09, U-23 |
| Claude Code mods | U-27, U-28, U-29, (U-09), (U-18 대안) |
| 정책·행동 지침 | U-16/U-32, 레포 `AGENTS.md` |
| 개발 방법론 | U-49, U-33, U-22, 레포 스킬 |

## 레포 기존 스킬과의 겹침 (REQ-SRC-007)

| 레포 스킬 | 겹치는 항목 | 1차 의견 |
|---|---|---|
| systematic-debugging | U-49(원본) | 새 경로는 superpowers 원본을 쓴다. 레포 스킬은 restricted 경로에서만 쓴다 |
| tdd-automator | U-49, U-33 | 새 경로는 superpowers TDD를 쓴다. 레포 스킬에만 있는 부분은 overlay로 남긴다 |
| submission-validator | U-49(verification-before-completion) | 새 경로는 원본에 레포 스킬의 고유 점검(파일명·형식)을 합친다 |
| task-router | U-49(brainstorming, writing-plans), 오케스트레이션 묶음 | P4-T3에서 비교 |
| implementation-review, design-review | U-49(requesting-code-review), U-22 | P4-T3에서 비교 |
| codebase-explorer | 코드 인덱싱 묶음 | 외부 후보는 모두 훅이나 인덱스를 설치한다 → 비교한 뒤 결정 |
| counterexample-hunter, algorithm-options | — | 원문 REQ-CE-001과 REQ-ALGO-001을 이 두 스킬을 확장해서 처리한다(Q7 승인) |
| algorithm-optimizer, benchmark | — | 유지 |
