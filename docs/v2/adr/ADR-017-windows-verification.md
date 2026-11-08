# ADR-017: Windows 검증 방법
- 상태: 승인(2026-11-05)
- 관련: D-17
- 날짜: 2026-11-05

## 배경
원문은 Claude Code가 Windows를 직접 실행할 수 없다고 가정했다. 실제로는 **이 PC가 Windows 11 Pro**다.
- 있는 것: PowerShell 5.1, Python 3.12, Git Bash, shellcheck
- 없는 것: pwsh 7, Linux, Python 3.9

근거: `baseline/test-baseline.md`.

## 선택지
1. Windows 항목은 이 PC에서 직접 실행해 `VERIFIED-RUN`으로 표시한다. Linux, pwsh 7, Python 3.9는 `NOT RUN`으로 두고 수동 체크리스트를 만든다.
2. 원문 그대로 Windows를 `NOT RUN`으로 둔다(사실과 다르다).

## 결정
**선택지 1.**
- 환경 표기는 `Windows 11 / PowerShell 5.1`, `Windows 11 / Git Bash`로 한다.
- Linux·macOS·pwsh 7·Python 3.9용 수동 검증 스크립트 `devtools/manual_verify.{sh,ps1}`와 체크리스트를 만든다.
- CI(GitHub Actions)는 push가 필요하므로 별도 승인 사항이다.

## 근거
P1 기준선에서 확인한 실행 환경.

## 결과와 위험
- 위험: Python 3.9에서만 드러나는 문법 오류(예: `X | None`의 런타임 평가)를 놓칠 수 있다.
  - 가능하면 `uv python install 3.9`로 직접 실행한다. 다만 네트워크 승인이 필요하다.
  - 그 전에는 ruff의 `target-version = "py39"` 규칙으로 정적 검사를 한다.

## 되돌리는 방법
되돌릴 것이 없다(검증 방법에 관한 결정이다).
