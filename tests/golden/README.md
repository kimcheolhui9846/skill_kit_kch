# 골든 회귀 테스트 (P3-T1)

서브커맨드 없이 실행하는 기존 경로가 v2 작업 중에도 그대로인지 확인한다(REQ-COMPAT-001, ADR-002).

| 파일 | 내용 |
|---|---|
| `cases.py` | 24개 경우: 5개 프로필 × {기본, dry-run, verify-only, no-mcp}, 3회 반복, 기존 AGENTS.md, 고친 구간, 키트 자신을 대상으로 지정. 정규화 함수 |
| `baseline/*.json` | P1-T3 기준선(`docs/v2/baseline/install-snapshots/`)의 사본. **고치지 않는다** |
| `inprocess/*.json` | 프로세스 안에서 실행한 골든(가짜 도구 탐지 + `no_network`). 보고서 전문을 담는다 |
| `test_golden_legacy.py` | 두 층의 비교와 `no_network` 픽스처 자체 검사 |

## 두 층

1. **기준선 비교(subprocess):** 실제 진입점 `python -I run_kit.py`의 종료 코드, 설치 트리 해시, HOME 무변경을 P1 기준선과 비교한다. 이 값들은 설치된 도구와 무관하므로 어느 PC에서도 같다.
2. **보고서 비교(in-process):** `kit.app.run`을 가짜 도구 탐지와 네트워크 차단 아래에서 실행해 정규화한 보고서 전문을 비교한다. 종료 코드와 트리도 기준선과 맞는지 확인한다.

## 정규화

- 대상 경로는 `<TARGET>`, 키트 경로는 `<KIT>`로 바꾼다.
- `YYYYmmdd-HHMMSS`는 `<STAMP>`로 바꾼다.
- `Environment:` 줄은 `<ENV>`로 바꾼다.
- `.kit/logs/`는 트리에서 제외한다.

in-process 보고서는 실제 기준선 보고서와 비교해 도구 버전 3줄만 다르다. `python`/`data`/`full`의 dry-run에서 `tool:pytest`, `tool:ruff`가 `fake 1.0`으로 표시되는 줄이다. 그 밖의 줄은 모두 같다(2026-11-06 확인).

## 갱신

기존 경로의 출력을 바꾸는 변경은 원문 A.3-1에 따라 중간 승인 대상이다. 승인을 받은 경우에만 다음 명령으로 `inprocess/`를 다시 만든다.

```
UPDATE_GOLDEN=1 uv run pytest tests/golden
```

`baseline/`은 갱신하지 않는다. 기준선이 바뀌어야 한다면 그 자체를 별도로 승인받는다.
