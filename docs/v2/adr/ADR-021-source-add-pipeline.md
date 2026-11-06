# ADR-021: 외부 소스 추가 파이프라인
- 상태: 승인(2026-11-05)
- 관련: D-21, REQ-SRC-009
- 날짜: 2026-11-05

## 배경
검토자는 나중에 GitHub 주소만 주면 그 스킬이 레포에 반영되기를 원한다(2026-11-05 승인). 상세 설계: `docs/superpowers/specs/2026-11-05-source-add-design.md`.

## 선택지
1. CLI(`kit source add|list|check|update|remove`)가 결정적인 처리를 맡고, 에이전트 스킬 `add-skill-source`가 설명과 승인 절차를 맡는다.
2. 에이전트 스킬만 둔다.
3. git submodule/subtree를 쓴다.

## 결정
**선택지 1.** 처리 순서:
1. 커밋 SHA로 고정한다.
2. `codeload` tarball을 `urllib`로 `.kit/incoming/`에 격리해 받는다. 받은 파일은 실행하지 않는다. 경로 탈출, 링크, 크기를 검사한다.
3. 라이선스 표(D-09)에 따라 vendored는 `third_party/<owner>-<repo>/`에 두고, 나머지는 reference로 남긴다.
4. 비밀값, 원격 실행, 바이너리, 숨은 유니코드를 스캔한다.
5. 공식 제약만 검증한다(R-7).
6. 겹침은 D-20 규칙으로 판정한다.
7. plan → 승인 → 원자적 반영 → `sources.lock.json`, NOTICES, 카탈로그에 기록한다.

스펙 문서는 vendored 위치를 `shared/skills/<name>/`로 적었지만, 이 ADR에서 `third_party/`로 바꾼다(D-01, D-09와 일치).

## P4-T8 구현에서 정한 것 (2026-11-06)
- **내려받기:** tarball은 `.kit/incoming/`에 풀지 않고 메모리에서만 다룬다. 승인 전에는 디스크에 아무것도 쓰지 않는다. gzip은 상한 + 1 MiB까지만 읽는다(압축 폭탄 방지).
- **링크:** 링크는 따라가지 않는다. 고른 스킬 폴더 안에 있을 때만 차단하고, 저장소의 다른 곳에 있는 링크는 무시한다.
- **이름 충돌:** verbatim 파일은 frontmatter `name`과 폴더 이름이 같아야 하므로, 스펙이 제안한 `<owner>-<name>` 개명은 할 수 없다. 이름이 겹치면 2로 끝내고 사람이 정한다.
- **MCP·플러그인:** `referenced`로만 기록한다. 버전을 고정한 카탈로그 항목은 사람이 쓴다.
- **네트워크 코드:** `kit/github_fetch.py` 한 파일에만 둔다. 이 파일은 api.github.com과 codeload.github.com에서 읽기만 한다. `tests/test_security.py`가 이 두 호스트만 있는지, 쓰기 메서드와 실행 호출이 없는지 검사한다. 나머지 `kit/*.py`의 네트워크 import 금지는 그대로다.
- **감지 패턴:** 원격 스크립트 실행 문구 같은 패턴은 `kit/source_scan.py`에만 둔다. 보안 테스트의 금지 문자열 검사에서 이 파일만 빼는 대신, 이 파일에 실행·네트워크 코드가 없는지 따로 검사한다.

## 근거
- 재현할 수 있고(SHA, 해시), 오프라인으로 테스트할 수 있다(tarball fixture). 에이전트가 바뀌어도 결과가 같다.
- 런타임 의존성이 없다(R-08).

## 결과와 위험
- 테스트 V-23: add → check → update → remove 왕복.
- 테스트 V-24: 라이선스가 없는 저장소는 vendored로 들어가지 않는다.
- 위험: GitHub API 호출 한도 → `GITHUB_TOKEN`이 있으면 쓰되 값은 출력하지 않는다.

## 되돌리는 방법
항목 하나는 `source remove`로 되돌린다. 기능 전체는 서브커맨드 등록을 해제하면 꺼진다.
