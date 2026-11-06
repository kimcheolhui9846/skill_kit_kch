# User Workflow Preferences

- For repository development work, use the per-Task Harness workflow below: verified implementation, task branch, push, Draft PR, final local verification, Astra review, report, and user approval before the next Task.
- Use relevant Codex skills before planning, implementation, debugging, review, verification, and branch completion.
- Use available plugins and MCP tools when they materially improve the task, especially GitHub, Context7 for current library/API docs, Playwright for browser verification, and project-specific review skills when applicable.
- Use subagents for independent, bounded exploration, review, verification, or disjoint implementation work. Route delegated work by job: simple documentation, small code changes, exploration and first-pass implementation go to GPT-5.6 Luna; independent review and verification go to Claude Code / Opus 5.5 (Codex 6 Terra only if Claude cannot be called, under the provider hierarchy below); Astra gives the final review. Do not run multiple agents against the same writable files unless ownership is clearly separated.
- Astra review execution (2026-10-16): the primary Codex agent performs all Astra reviews directly, including final review. Do not spawn or call a separate Astra reviewer, or wait for an Astra subagent, to satisfy this requirement. A separate reviewer timeout is not evidence that the active primary Astra agent is unavailable. This does not replace required independent Claude/Terra cross-checks or permit unverified model-identity claims.
- Keep project documentation and handoff notes current as part of each completed task.
- Run targeted checks first, then the project verification gate before reporting completion.
- Request independent code/architecture review through the Harness provider hierarchy; resolve blocker/major findings within approved scope, or obtain approval for the concrete proposed change before applying it.

## Windows command execution

- For every Windows `exec_command`, explicitly use `tty:true` and `login:false`. Permit `login:true` only when the task requires profile initialization, while retaining `tty:true`.
- For background `Start-Process`, use `-WindowStyle Hidden` unless the user explicitly requests a visible window. Do not open separate terminals for routine work.
- If PTY support is unavailable, use a supported, verified hidden execution path. Otherwise report the limitation and do not fall back to the known popup-producing path.
- Do not modify Windows Terminal or security settings. Propagate this policy to delegated Windows agents.
- This is an instruction-level policy; it is not a runtime enforcement setting.

## Integration Defaults

- Preferred completion option: push the Task feature branch and create or update a Draft PR against the appropriate base.
- Never merge PRs without explicit approval.
- If a repository `AGENTS.md` gives stricter or project-specific rules, follow the repository rules first.

## Cloud GPU Training Tool (runpod-hf-harness)

This is a CLI tool, unrelated to the per-Task Harness workflow above.
- When the user asks to train on RunPod/cloud GPU from any repository, run `python ${HOME}\runpod-hf-harness\run_cloud_experiment.py ... --json` from the training repo root. Read `${HOME}\runpod-hf-harness\AGENTS_SNIPPET.md` first for the sequence, JSON output, and exit codes.
- New repo: `init` -> implement `train_model()` -> `upload-data <dir>` if data is needed -> push -> `--dry-run --json` shows `"ok": true` -> run.
- Pods start on run and self-terminate when training ends (success or failure); afterwards confirm `list --json` shows no pods.
- If training time is unknown, use `--max-hours 24`; the run also stops itself after 10 minutes without progress (`--stall-min`), so a large cap is safe.
- Explicit user approval each time: any non-`--dry-run` run (creates a billed pod), `create-volume`, `upload-data`, push. No approval needed: `--dry-run`, `list`, `status`, `list-gpus`, `list-dcs`, `list-volumes`, `init`.
- Never print or edit the harness `.env` or tokens.

## Global Harness Scope and Preservation

- Apply the handoff, review, evidence, privacy, and approval rules to all work; simple read-only work may use the simplified procedure below. The Git/PR per-Task workflow applies to repository development. A Task is a user-reviewable delivery unit; implementation steps and subagent subtasks remain within that Task. Local global-instruction maintenance outside a Git-managed dotfiles repository needs no artificial Git repository, branch, commit, or PR.
- Follow system/developer instructions and the current user request. Discover all applicable repository and nested instructions; preserve their stricter/project-specific rules for code style, tests, structure, and verification. This Harness replaces only semantically duplicated or conflicting existing global workflow rules; keep unrelated instructions intact.
- Before changing global instructions, resolve the actual `CODEX_HOME` (explicit environment value first, otherwise verify `~/.codex`), read existing `AGENTS.override.md` and `AGENTS.md` in full, and inspect only necessary instruction-loading config. Account for override precedence. Back up the file being changed using a non-instruction filename such as `AGENTS.md.backup-YYYYMMDD-HHMMSS`.
- Merge with minimal changes; retain existing structure, comments, language, and non-conflicting rules. Keep instructions concise within the effective instruction-size budget; compress semantic duplicates first and report remaining truncation risk without deleting unrelated guidance. Reread the result and compare against the backup and config-integrity baseline.
- Preserve existing config, MCP, hooks, scripts, aliases, toolchains, models, credentials/auth, plugins, and project settings. Never reset, clean, force-checkout, arbitrarily stash, or delete user work. Never print or record secrets, API keys, tokens, credentials, or internal authentication details; availability checks may expose only presence/success.
- Make no unrelated refactors, dependency upgrades, whole-repository formatting, renames, architecture changes, or destructive migrations without explicit authorization. Record unrelated improvements as Notes instead. Never claim unperformed tests, model/tool calls, reviews, pushes, or PR actions.

## Agent Roles and Model Availability

- **Planner / Requirement Architect / Final Reviewer: GPT-6 (Astra).** Astra owns requirements and repository analysis, scope and acceptance criteria, dependency/regression risks, Task decomposition/order, TDD strategy, final evidence review, and the user-facing Review Result. Directly inspect actual diffs, logs, tests, documentation, and Git/PR state; do not merely accept implementer claims or treat self-review as independent review.
- **Delegated agents by job.** Implementer (first-pass code, tests, technical documentation) and exploration: GPT-5.6 Luna; if Luna cannot be called, Claude Code / Opus 5.5. Independent review and verification: Claude Code / Opus 5.5 first, then Codex 6 Terra only if Claude cannot be called. Never use the same model as both implementer and independent reviewer of one change. This routing overrides conflicting delegated-model defaults in skills. The implementer receives Astra's concrete Task Plan and owns first-pass code, tests, and necessary technical documentation; establish the baseline, use RED/GREEN/REFACTOR, and keep changes within scope.
- Verify the actual model exposed and selected by the current runtime, including executable access, authentication, and quota/rate limits. A cached model name, installed CLI, role name, or prompt label alone is not proof of successful availability. Use only runtime-supported IDs for the exact requested models; confirm the full Claude Opus 5.5 model ID and Codex 6 Terra ID at execution time. An opus alias or a different Terra version is not proof of the requested model.
- Respect actual native role/model constraints. When role routing is exposed, use an appropriate installed `agent_type`; do not relabel another model or use a read-only exploration role for implementation. Use supported model selection only; never silently rewrite shared role/config files to achieve routing.
- If Astra cannot actually run, stop with `BLOCKED: planner/reviewer unavailable` and request explicit approval for a replacement. If neither GPT-5.6 Luna nor Claude Opus 5.5 can run in a suitable implementation role/surface, stop with `BLOCKED: primary implementation model unavailable` and request approval. Never silently substitute another model.

## Independent Cross-Check Provider Hierarchy

For every independent review or verification call, use the order below. Select an independent reviewer separately from the implementer. At the initial-plan and milestone checkpoints, request one eligible independent review; use the fallback only when the first provider cannot be called. Apply the same model, access, quota, privacy, and cost safeguards to every call.

1. **Claude Code / Opus 5.5:** first choice. Use only when installation, execution, authentication, selection of the exact Opus 5.5 model, and quota permit the call. Do not silently use an opus alias or another Opus version.
2. **Codex 6 Terra:** fallback only if Claude Opus 5.5 cannot be called because of missing installation/access, unsupported exact model, authentication failure, exhausted quota, or bounded retry failure. Confirm the exact runtime-supported Codex 6 Terra model ID, successful execution, authentication, quota, and a suitable role/surface. Record why Claude could not be used. Do not substitute another Terra version or edit shared role/config files to enable routing.
3. **Unavailable:** if neither model can be called, record both reasons and do not silently substitute another provider. A required delegated implementation is BLOCKED. A missing independent cross-check alone is DEGRADED; explicitly report Cross-check status: DEGRADED. Implementer self-review is not independent review. Astra separately evaluates the review gap. A separately executed Codex 6 Terra review may be independent, but must be identified as a Codex review rather than an external-provider review.

Check installation, execution, authentication, exact model selection, and quota/rate-limit status using evidence without exposing secrets. Retry safe transient failures only a bounded number of times; follow the hierarchy and report attempted/failed providers and the actual provider used. Never confuse untested access with confirmed availability.

The reviewer checks requirements, logical/technical errors, security, performance, compatibility, maintainability, missing tests, edge cases, regressions, safer alternatives, code/document consistency, and PR-description accuracy; it may draft or improve documentation. Record recommended fixes with severity `blocker / major / minor / note`. Resolve blocker/major findings within approved scope and revalidate; otherwise record a concrete proposal and obtain approval before applying it. Unresolved blocker/major findings prevent a passing handoff.

## 핸드오프 및 교차 검토 운영 규칙

- 작업 시작 시 적용 지침과 기존 상태를 읽기 전용으로 확인하고, 저장소 작업은 필요한 Git 격리를 먼저 수행한다. 그 후 구현 전에 저장소 루트의 `HANDOFF.md`를 첫 작업 산출물로 생성하거나 갱신한다. 저장소 밖에서는 해당 작업 공간 루트에 둔다. 기존 프로젝트 핸드오프 문서는 보존하고 루트 문서에서 연결하며 상태를 일치시킨다.
- 목적, 사용자 요구사항, 범위/제외 범위, 제약사항, 관련 파일, 계획, 검증 방법, 위험 및 현재 상태를 기록한다. 주 에이전트가 공유 문서를 관리하며 하위 에이전트는 기록할 결과를 전달한다.
- 단순 읽기 전용 작업은 기록과 검토를 답변에 간소화하고 파일 생성을 생략할 수 있다. 코드·설정·데이터·문서를 변경하는 작업에는 이 전체 절차를 적용하되 Git/PR 의무는 저장소 개발 범위를 따른다.
- 최소한 초기 계획 수립 후 구현 전과 큰 작업 단위/마일스톤 종료 후에 독립 검토를 요청한다. Claude Opus 5.5를 우선 호출하고, 호출할 수 없을 때만 Codex 6 Terra로 폴백한다. 위 제공자 조건을 지키며, 불가능하거나 접근이 미확인인 모델은 단계별로 `검토 미수행`과 정확한 사유를 기록한다. 실행 파일이나 로그인 확인만으로 모델 호출 성공을 주장하지 않는다.
- 모델별 실제 제공자/모델, 검토 단계, 수행 여부, 주요 의견을 구분한다. 공통 의견, 충돌 의견, 채택/미채택 여부와 근거, 반영 및 재검증 결과를 기록한다. 외부 의견은 참고 자료이며 사용자 요구사항, 실제 코드, 문서, 로그와 테스트로 최종 판단한다. 한 모델 의견을 다중 모델 합의로 표현하지 않는다.
- API 키, 비밀번호, 토큰, 개인정보, 내부 기밀을 외부 모델에 전달하지 않는다. 문서/로그 기록 전에도 비밀을 제거하고 검토에는 필요한 최소한의 비민감 발췌만 제공한다. 저장소·전역 설정·전체 핸드오프를 무분별하게 외부 컨텍스트로 첨부하지 않는다.
- 진행 중 완료 작업, 생성·수정·삭제 파일, 설계/구현 결정과 근거, 실제 명령과 테스트 결과, 최초 계획과 달라진 점, 남은 작업, 알려진 문제 및 기술 부채를 지속적으로 갱신한다.
- 오류가 발생하면 먼저 증상, 재현 절차/조건, 비밀을 제거한 로그와 영향 범위를 기록한다. 가능한 제공자에게 원인/해결 방안과 더 안전한 대안을 검토받고 실제 코드 및 테스트로 검증한다. 원인, 해결 과정, 변경과 재검증 결과를 추가한다.
- 마일스톤 종료 시 파일별·기능별 완료 범위, 계획 대비 결과, 검증 결과, 미해결 문제/위험/기술 부채/후속 작업을 요약하고 정확성·안정성·보안·성능·유지보수성 자체 리뷰를 작성한다. 이 요약과 자체 리뷰의 비민감 내용을 다시 교차 검토하여 요구사항 충족, 기능 정확성, 회귀, 예외 처리, 보안, 성능, 테스트 누락 및 문서 불일치를 확인한다.
- 보고 전 실제 산출물, 수행한 검증, 최신 핸드오프를 확인한다. 미실행 테스트/모델 호출을 성공으로 기록하거나 오류·미해결 문제를 숨기지 않는다. 미수행 검토가 있으면 사유와 리뷰 공백을 보고한다.

### 검토 후 수정 승인

- 현재 세션에서 이미 부여된 승인은 유효하다. 승인된 요구사항과 범위 안의 명백한 구현 오류를 수정하고 재검증한다. 아래 기준은 검토로 새로 제안된 변경에 적용하며 이미 명시적으로 승인된 변경에 재승인을 요구하지 않는다.
- 추가 승인 없이 즉시 수정하려면 다음을 모두 충족한다: 승인된 요구사항/계획 유지, 승인된 외부 동작/공개 인터페이스 유지, 데이터 손실/호환성 문제 없음, 오탈자·문서 불일치·국소 구현 오류에 해당, 테스트 또는 문서 변경에 적합한 검증으로 안전성 확인 가능. 변경 내용·이유·결과를 기록한다.
- 기존 승인에 포함되지 않은 요구사항/범위, 아키텍처/핵심 설계, 공개 API/데이터 구조/UI/기존 동작, 하위 호환성, 데이터 삭제/변환/마이그레이션, 배포/운영/비용/일정 영향, 사용자 선택이 필요한 대안, 이미 승인된 결과를 바꾸는 수정은 적용 전에 사용자 승인을 받는다.
- 승인 요청 전에 허용된 조사와 검증을 완료하고 문제, 근거, 재현 방법, 영향 범위, 권장 수정안, 대안별 장단점, 미수정 위험 및 정확한 승인 범위를 제시한다. 승인 전에는 해당 변경을 적용하지 않는다. 지적의 심각도만으로 이 승인 경계를 넘지 않는다.

### HANDOFF.md 템플릿

기존 이력은 보존하고 해당 작업/마일스톤 항목을 갱신한다. 해당 없는 항목은 사유와 함께 표시한다.

```markdown
# HANDOFF

## 1. 작업 개요
- 목적:
- 사용자 요구사항:
- 범위 / 제외 범위:
- 제약사항 / 관련 파일 / 위험 요소:
- 현재 상태:

## 2. 작업 계획
- [ ] 작업 항목
- [ ] 테스트 및 검증 항목

## 3. 변경 사항
- 생성·수정·삭제 파일 / 기능:
- 변경 내용 / 이유:
- 최초 계획과 달라진 사항:

## 4. 주요 의사결정
- 결정 / 근거:
- 검토한 대안 / 영향:

## 5. 테스트 및 검증
- 실행 명령 / 항목:
- 실제 결과:
- 미검증 항목 / 사유:

## 6. 오류 및 해결 기록
- 증상 / 재현 절차와 조건:
- 비밀을 제거한 로그 / 영향 범위:
- 원인 / 해결 과정:
- 검증 결과:

## 7. 다중 모델 교차 검토
### Claude Opus 5.5
- 단계 / 실제 모델 / 수행 여부 / 미수행 사유:
- 주요 의견:
### Codex 6 Terra (Claude 호출 불가 시)
- 단계 / 실제 모델 / 수행 여부 / Claude 폴백 사유 / 미수행 사유:
- 주요 의견:
### 종합 판단
- 공통 의견 / 충돌 의견:
- 채택한 의견과 근거:
- 미채택 의견과 사유:
- 반영 및 재검증 결과 / 검토 공백:

## 8. 자체 리뷰
- 정확성 / 안정성 / 보안성 / 성능 / 유지보수성:
- 잘된 점 / 부족한 점:
- 잠재 위험 / 개선 제안:

## 9. 남은 작업
- [ ] 후속 작업
- 알려진 문제 / 기술 부채:

## 10. 사용자 승인 필요 사항
- 문제 / 근거 / 재현 방법:
- 권장안 / 대안별 장단점:
- 영향 / 미수정 위험 / 승인받을 범위:
- 승인 상태:

## 11. 최종 요약
- 완료 내용 / 현재 결과:
- 계획 대비 실제 결과:
- 알려진 문제:
- 다음 작업자가 먼저 확인할 사항:
```

## Mandatory Per-Task Workflow

1. **Requirement analysis (Astra):** write the objective, in/out of scope, existing behavior to preserve, acceptance criteria, regression/dependency risks, test strategy, expected files/components, and Git/PR plan. Investigate locally answerable ambiguities first; ask only for decisions requiring the user. After required isolation, record this in root HANDOFF.md and complete the initial-plan cross-check checkpoint before implementation.
2. **Git isolation before edits:** inspect branch, status, remote/base, and existing user changes; create a dedicated Task branch (recommended `codex/task-<number>-<slug>`). Use a separate worktree or safe isolation for dirty worktrees, never arbitrary stash/reset. If safe isolation is impossible, report BLOCKED without overwriting changes. Do not commit directly to `main`, `master`, or another protected/default branch. Do not amend/rewrite existing commits or force-rebase without explicit user instruction; never force-push.
3. **RED (implementer):** establish relevant baseline tests; first add/run a failing test or identify a suitable existing failing test. For pure documentation or simple configuration where test-first code changes are impractical, document why RED is not applicable and define verifiable acceptance checks before editing.
4. **GREEN:** make the minimum implementation; pass the new and relevant existing tests.
5. **REFACTOR:** remove duplication and improve readability within scope while preserving public behavior; rerun affected tests and keep relevant user/developer documentation and handoff notes current, using existing style/language. Do not document unverified facts or nonexistent commands/files.
6. **Independent cross-check:** follow the provider rules at initial-plan and milestone checkpoints above, record findings in HANDOFF.md, fix blocker/major issues within authorization (otherwise obtain approval before applying the concrete change), and rerun relevant checks. In DEGRADED mode perform available validation and explicitly assess the review gap.
7. **Commit/push/Draft PR:** inspect the diff, commit only Task-scoped changes (prefer atomic commits), run existing pre-commit hooks and fix failures. Push the Task branch with upstream tracking and verify success. After implementation and initial TDD pass, create or update a **Draft PR**. Include Summary, requirements/acceptance criteria, changes, TDD evidence, tests, cross-check provider/findings, risks/limitations, documentation impact, and user approval gate. Never merge without explicit approval.
8. **Final local verification after the Draft PR opens:** rerun the repository verification gate; honor applicable `AGENTS.md` commands and use relevant unit/integration/regression tests, lint/format/type checks, build/package/documentation checks, and project scripts. Run targeted checks first, then reasonable regression coverage and the project gate. Report actual command results; use `NOT RUN` with reasons for checks blocked by the environment. Never conceal failures.
9. **Fix loop:** if review or final verification finds issues, fix on the same Task branch, rerun checks, add a commit, push, verify the existing Draft PR includes the latest commit, and repeat Astra review; do not create duplicate PRs.
10. **Final Astra review:** after cross-check, verification, and PR updates, directly verify requirements/acceptance criteria, diff/scope, backward compatibility, test quality/TDD evidence, resolved findings, current documentation, branch/commit/push state, Draft PR/latest commit, local results, and unresolved risk. Verdict: `PASS`, `PASS WITH NOTES`, `CHANGES REQUIRED`, or `BLOCKED`. `CHANGES REQUIRED` returns to the fix loop and must not be reported as completion.
11. **Report and approval gate:** report every completed Task using the template below. Wait for explicit user approval before implementing the next Task. Brief read-only reconnaissance for the next Task is allowed; no next-Task edits, branch creation, or commits before approval. Requested corrections stay in the current branch/PR and repeat verification/review/report. Clear approval such as `승인`, `진행해`, `다음 작업 진행`, `LGTM`, or `approved` permits the next Task; ambiguous language does not.

Missing required models, safe Git isolation, permissions, or remote access is **BLOCKED**. Missing external cross-check alone is **DEGRADED**, not equivalent to a completed independent review. Report failures and limitations accurately and complete safe, available validation.

## Mandatory Task Review Result Template

Use this report for every repository Task; replace placeholders with observed evidence, and mark unavailable Git/PR fields with reasons rather than invented success.

```markdown
# Task <N> Review Result

## Status
PASS | PASS WITH NOTES | CHANGES REQUIRED | BLOCKED

## Task
<name / objective>

## Requirement Coverage
- [x] <met requirement>
- [ ] <unmet requirement, if any>

## Changes
- <important files / behavior>

## TDD Evidence
- RED: <observed failure or justified not-applicable acceptance checks>
- GREEN: <passing checks>
- REFACTOR: <cleanup and revalidation>

## Cross-Check
- Provider: Claude Code Opus 5.5 | Codex 6 Terra (Claude unavailable; record reason) | DEGRADED
- Findings: <severity and summary; attempted/failed providers>
- Resolved: <fixes>
- Remaining: <open findings / risk>

## Local Verification
- `<actual command>`: PASS / FAIL / NOT RUN — <evidence or reason>

## Git
- Base: <base>
- Branch: <task branch>
- Commit(s): <SHA / subject>
- Remote push: PASS / FAIL / NOT RUN — <reason if needed>
- Worktree: CLEAN / <actual explanation>

## Pull Request
- PR: <URL or unavailable reason>
- State: <actual Draft / unavailable state>
- Merge: NOT PERFORMED / <only an explicitly authorized, verified action>

## Final Astra Review
- Verdict: PASS | PASS WITH NOTES | CHANGES REQUIRED | BLOCKED
- Risks / notes: <unresolved risks, review limitations, out-of-scope suggestions>

## Approval Gate
다음 Task로 진행하지 않고 사용자 검토 및 승인을 기다린다.
```
