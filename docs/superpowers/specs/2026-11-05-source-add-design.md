# 설계: GitHub 주소로 스킬 추가하기 (`kit source add`)

- 날짜: 2026-11-05
- 상태: 승인됨(2026-11-05). `00_ADDENDUM.md` REQ-SRC-009, ADR D-21로 확정.
- 요청(검토자 원문): "나중에 언제나 좋아보이는 스킬 발견해서 그 깃허브 레포 주소를 주면 그 스킬도 레포에 반영하게 설계해봐"

> **P4-T8 구현(2026-11-06):** 스펙과 달라진 점은 ADR-021 "P4-T8 구현에서 정한 것"에 있다(메모리에서만 풀기, 이름 충돌은 개명하지 않고 2, MCP·플러그인은 referenced만, 네트워크 코드는 `kit/github_fetch.py` 하나).
>
> **ADR-021 반영(2026-11-05):** vendored 외부 파일의 위치는 `shared/skills/<name>/`가 아니라 `third_party/<owner>-<repo>/`다(D-01, D-09). 아래 본문의 `shared/skills/<name>/`는 이 위치로 읽는다. `shared/skills/`에는 키트가 작성한 스킬만 둔다.

## 1. 목표

검토자가 언제든 GitHub 저장소 주소 하나를 주면, 그 저장소의 스킬(또는 MCP·플러그인)이 다음 단계를 거쳐 레포에 들어온다.

1. 확인: 저장소, 라이선스, 커밋을 확인한다.
2. 검사: 보안과 형식을 검사한다.
3. 겹침 판정: 기존 스킬과 겹치는지 판정한다.
4. 계획 표시와 승인: 무엇이 바뀌는지 보여 주고 승인을 받는다.
5. 반영: `shared/skills/`, `sources.lock.json`, NOTICES, 카탈로그·프로필에 반영한다.

반영 뒤에는 다른 PC에서도 `install` 한 번으로 그 스킬이 설치된다(REQ-USER-001~005와 같은 흐름).

요청 경로는 두 가지다.

- **대화로 요청**: Claude Code나 Codex 대화창에 주소를 붙여 넣는다. 에이전트가 레포 안의 `add-skill-source` 스킬을 따라 아래 CLI를 부른다.
- **직접 실행**: `python -m kit source add <url>`을 직접 실행한다.

## 2. 비교한 방식

| 안 | 내용 | 판단 |
|---|---|---|
| **A (권장)** | 결정적인 처리는 CLI가 맡는다: 고정, 내려받기, 검사, 기록. 판단과 설명은 에이전트용 스킬이 맡는다 | 결과를 재현할 수 있고 테스트할 수 있다. 에이전트가 바뀌어도 같은 결과가 나온다 |
| B | 에이전트 스킬만 둔다(수동 절차서) | 구현은 가장 적다. 그러나 매번 결과가 달라지고, 고정·해시 기록이 빠지기 쉽다 |
| C | git submodule/subtree로 저장소 전체를 넣는다 | 필요 없는 파일, 실행 스크립트, 라이선스가 맞지 않는 파일까지 따라온다. 원문 D-09(작은 텍스트만 넣는다)와 맞지 않는다 |

## 3. 명령

```
python -m kit source add <github-url> [--ref <tag|branch|sha>] [--path <저장소 안 경로>]
                                      [--name <스킬 이름>] [--pack <팩>] [--yes] [--json]
python -m kit source list   [--json]
python -m kit source check  [--json]        # 오프라인: 기록된 해시와 실제 파일 비교
python -m kit source update <name> [--ref …] # 새 커밋으로 다시 고정(add와 같은 절차)
python -m kit source remove <name>
```

- 받는 주소 형식은 `https://github.com/<owner>/<repo>`, `.../tree/<ref>/<path>`, `<owner>/<repo>`다. `tree/<ref>/<path>` 형식이면 `--ref`와 `--path`를 주소에서 읽는다.
- 기본값은 계획만 보여 준다. 실제로 쓰려면 TTY에서 확인하거나 `--yes`를 준다(REQ-USER-002와 같은 규칙).
- 종료 코드는 기존 체계를 따른다.

| 코드 | 뜻 |
|---|---|
| 0 | 완료, 또는 계획만 표시 |
| 1 | 검사 실패(차단) |
| 2 | 사람의 판단이 필요(`NEEDS_HUMAN`) |
| 64 | 사용법 오류 |
| 65 | 입력 오류 |

## 4. 처리 흐름

```
resolve → pin → fetch(격리) → detect → license → scan → validate → overlap → plan → [승인] → apply → verify → record
```

| 단계 | 하는 일 | 실패 시 |
|---|---|---|
| resolve | 주소를 해석한다. GitHub API로 저장소가 있는지 보고, 이름이 바뀌었으면(redirect) 새 이름을 쓴다. 보관(archived) 여부도 확인한다 | 없는 저장소면 65. archived면 경고 |
| pin | `--ref`(없으면 기본 브랜치)를 **커밋 SHA로 고정**한다 | — |
| fetch | `codeload.github.com/<o>/<r>/tar.gz/<sha>`를 `urllib`로 받아 `.kit/incoming/<o>-<r>-<sha7>/`에 푼다. 압축 해제 때 경로 탈출(`..`, 절대경로), 심볼릭 링크, 크기 상한(기본 20 MiB)을 검사한다. **받은 파일은 실행하지 않는다** | 차단(1) |
| detect | 종류를 판별한다. `SKILL.md`가 있으면 스킬이다(여러 개면 목록을 보여 주고 `--path`나 다중 선택). `.claude-plugin/plugin.json`이나 루트 `plugin.json`이면 플러그인이다. MCP 서버 패키지(README의 `mcpServers` 예시, `package.json` bin)면 MCP다. 아무것도 아니면 참조만 한다 | 판별 불가면 2 |
| license | LICENSE/COPYING 파일과 GitHub API의 SPDX를 대조한다 | 아래 표 |
| scan | 비밀값 패턴(기존 REQ-USER-004 스캐너를 재사용), `curl\|bash`/`iwr\|iex`, 실행 파일·바이너리, 절대경로·사용자 경로, 숨은 지시문(프롬프트 인젝션 의심 문구, 보이지 않는 유니코드)을 검사한다 | 비밀값·바이너리는 차단. 나머지는 경고와 `NEEDS_HUMAN` |
| validate | 공식 제약을 검사한다: frontmatter `name`·`description`, 이름 규칙, 길이. 키트 작성 규칙(“Do NOT use” 등)은 외부 스킬에 강제하지 않는다(R-7, P4-T2) | 공식 제약 위반은 1 |
| overlap | 기존 스킬과 비교한다: 이름 충돌, 그리고 description·본문 토큰의 Jaccard 유사도(임계값 설정 가능, 기본 0.5) | 아래 §5 |
| plan | 바뀔 파일, 라이선스, 커밋, 겹침 판정, 들어갈 팩, 경고를 표시한다. `--json`이면 기계가 읽는 형식으로 낸다 | — |
| apply | 원자적으로 쓴다: `shared/skills/<name>/`, `sources.lock.json` 항목, `NOTICES`의 출처·라이선스, 카탈로그와 팩 목록 | 실패하면 백업으로 되돌린다 |
| verify | 스킬 검증과 `source check`를 돌리고, 미러 고정 테스트(V-22)를 돌린다 | 되돌리고 1 |
| record | `07_SOURCES_EVALUATION.md`에 한 줄 평가를 덧붙인다 | — |

### 라이선스 처리

| 감지 결과 | 처리 |
|---|---|
| MIT, Apache-2.0, BSD-2/3, ISC, 0BSD, CC-BY-4.0, Unlicense | 파일을 레포에 넣는다. LICENSE 사본을 `shared/skills/<name>/LICENSE`로 두고 NOTICES에 기록한다 |
| GPL/AGPL/LGPL, `other`, 라이선스 없음 | **파일을 넣지 않는다.** `sources.lock.json`에 `mode: reference`로 주소와 커밋만 남긴다. 설치할 때는 "직접 설치 안내"만 출력한다(D-09). 검토자가 `--accept-license`로 명시해야 넣는다(`other`만 해당하고 기록이 남는다) |

## 5. 겹침 처리 (REQ-SRC-007 확장)

새로 추가하는 주소는 **사용자 목록과 같은 우선순위**로 본다. 검토자가 직접 고른 것이기 때문이다.

- 새 경로(standard, claude/both)에서는 새 스킬을 채택한다. 겹치는 기존 스킬은 그 팩에서 빼거나, 고유한 부분만 overlay로 남긴다. 어느 쪽으로 할지는 plan에 제안으로 보여 주고 승인받는다.
- restricted 경로와 미러 `.agents/skills`의 11개는 **절대 바뀌지 않는다**(REQ-COMPAT-002, R-3). 테스트 V-22가 이를 강제한다.
- 이름이 충돌하면 `<owner>-<name>`으로 바꾸자고 제안한다. 덮어쓰지 않는다.

## 6. 기록 형식 (`sources.lock.json`, JSON)

```json
{
  "name": "frontend-design",
  "kind": "skill",
  "mode": "vendored",
  "repo": "https://github.com/anthropics/skills",
  "path": "skills/frontend-design",
  "ref": "main",
  "commit": "<40자 SHA>",
  "license": "Apache-2.0",
  "added": "2026-11-05",
  "added_by": "source add",
  "packs": ["web"],
  "files": {"SKILL.md": "<sha256>", "LICENSE": "<sha256>"},
  "overlap": [{"with": "frontend-ui", "score": 0.62, "decision": "replace-in-standard"}]
}
```

- `source check`는 네트워크 없이 `files` 해시만 비교한다. 따라서 CI와 테스트에서 돌릴 수 있다.
- `source update`는 새 커밋과의 차이를 plan에 보여 준다. 기존 파일을 로컬에서 고쳤으면(해시 불일치) 덮어쓰지 않고 2로 끝난다.

## 7. 종류별 반영 범위

| 종류 | 레포에 넣는 것 | 설치할 때 |
|---|---|---|
| 스킬 | `SKILL.md`와 같은 폴더의 텍스트 참조 파일. 스크립트는 기본 제외하고, 검토자가 파일 단위로 승인하면 넣는다 | 프로젝트 `.claude/skills`, `.agents/skills`(새 경로만). user 범위는 `~/.claude/skills`, `~/.codex/skills` |
| MCP | 카탈로그 항목만 넣는다: 명령, **버전 고정한 패키지**, 필요한 환경 변수 *이름* | 기본은 꺼져 있다. 프로필이나 `--mcp`로 켠다(기존 허용 목록 방식) |
| 플러그인 | 선언만 넣는다: 마켓플레이스와 이름 | 설정에 선언하거나 안내를 출력한다(D-10) |
| 참조 | `sources.lock.json`의 주소와 커밋 | 안내만 출력한다 |

## 8. 에이전트용 스킬 `add-skill-source`

`shared/skills/add-skill-source/SKILL.md`에 둔다. 이 레포를 여는 Claude/Codex용이다.

- 트리거: 사용자가 GitHub 저장소 주소를 주며 "이 스킬 추가", "레포에 반영" 같은 요청을 할 때.
- 절차:
  1. `python -m kit source add <url> --json`으로 계획을 받는다.
  2. 사용자에게 다음을 요약한다: 라이선스, 커밋, 겹침, 경고, 들어갈 팩.
  3. 사용자가 승인하면 `--yes`로 다시 실행한다.
  4. 테스트를 돌린다.
  5. 결과를 보고한다.
- 금지:
  - 받은 저장소의 스크립트나 설치 명령을 실행하지 않는다.
  - 라이선스 판정을 임의로 바꾸지 않는다.
  - 커밋·푸시는 사용자가 요청할 때만 한다.
- 이 스킬은 키트를 개발하는 레포 쪽 도구다. 대상 프로젝트에 설치할지는 팩 설정에 따른다(기본은 설치하지 않음).

## 9. 오류와 경계

- 네트워크가 없거나 GitHub API 한도에 걸리면 2로 끝나고 이유를 표시한다. 환경 변수 `GITHUB_TOKEN`이 있으면 쓰되, 값은 출력하지 않는다(R-09).
- 한 저장소에 스킬이 여러 개 있으면(예: `anthropics/skills`) 목록을 보여 준다. 고르는 방법은 `--path`를 여러 번 주거나 `--all`이다.
- 같은 주소를 다시 추가하면 변경 없음(0)이다. 다른 커밋이면 `update`를 쓰라고 안내한다.

## 10. 테스트

모두 네트워크 없이 돌린다. fetch 단계는 tarball fixture로 대체한다.

- 주소 해석: 형식 3가지와 잘못된 주소(64)
- tar 안전성: `..`, 절대경로, 심볼릭 링크, 크기 초과를 모두 차단하는지
- 라이선스 표: 허용, copyleft, 없음, `other` 각각
- 스캐너: 비밀값, `curl|bash`, 보이지 않는 유니코드
- 겹침: 이름 충돌, 유사도 임계값
- 원자성: apply 중간에 실패하면 되돌리는지
- `source check`: 해시가 바뀌었을 때 탐지하는지
- V-22: restricted 경로와 미러가 바뀌지 않는지
- 같은 주소를 두 번 추가하면 변경이 없는지

## 11. 계획에 넣는 위치

- **P2-T1**: ADR **D-21** "외부 소스 추가 파이프라인"을 추가한다. 안 A를 택하고 tarball 방식, SHA 고정, 라이선스 표를 정한다.
- **P4-T8 (신규)**: `kit source` 명령과 `add-skill-source` 스킬을 만든다. P4-T3(평가)과 P4-T4(`sources.lock.json`)의 형식을 그대로 재사용하므로 **P4-T4 뒤에 한다.** P4-T3에서 49개를 반영할 때도 같은 파이프라인을 쓸 수 있으면 쓴다. 등급은 B다.
- **P6-T2**: V-23(오프라인 fixture로 add → check → update → remove를 왕복)과 V-24(라이선스가 없는 저장소는 vendored로 들어가지 않음)를 추가한다.

## 12. 하지 않는 것 (YAGNI)

- GitHub 외 호스트(GitLab 등)
- 자동 주기 업데이트
- 스킬 추천·검색 기능
- 받은 저장소의 빌드나 실행
