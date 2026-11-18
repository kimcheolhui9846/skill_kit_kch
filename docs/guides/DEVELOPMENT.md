# 개발과 공개 전 점검

키트 저장소 루트에서 개발 도구를 준비하고 검증합니다.

```bash
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run python devtools/make_examples.py      # docs/examples/*.log 재생성
uv run python devtools/make_catalog_doc.py   # docs/CATALOG.md 재생성
uv run python devtools/run_doc_commands.py   # 사용자 문서의 명령을 실행해 기록
shellcheck bootstrap.sh
```

## 공개 전 점검

- 라이선스와 저장소 주소를 확인한다.
- 저장소에 토큰, 개인 경로, 시험 관련 비공개 자료가 없는지 확인한다.
- [테스트 보고서](../TEST_REPORT.md)를 확인한다.
