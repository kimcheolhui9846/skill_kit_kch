## Codex와 Claude Code의 공동 작업

이 절은 두 도구를 함께 쓰는 개발 작업의 기본 모델 배정을 정한다. 이전의 일반 역할 배정과 충돌하면 이 순서를 따른다. 저장소별 검토 등급, 외부 호출 제한, 사용자 승인과 비용 한도는 해당 프로젝트의 지침을 따른다.

1. **계획과 설계**는 주 Codex 세션의 GPT-6.2 Astra(`gpt-6.2-astra`)가 맡는다. 요구사항, 수용 기준, 변경할 파일과 테스트를 정리한다. Claude Code에서 시작했다면 실제 Astra 세션에 계획을 맡기고, 최종 검토에 사용할 세션 ID를 보관한다.
2. **계획 교차 검토**는 Claude Opus 5.5(`claude-opus-5-5`, `harness-opus-review`)가 맡는다. 허가된 최소한의 자료로 설계와 검증 방법을 확인한다. 수정 의견은 Astra가 반영하고 Opus의 통과 판정을 받은 뒤 구현을 시작한다.
3. **문서와 작은 구현 작업**은 GPT-6.2 Sol(`gpt-6.2-sol`, `harness-sol-worker`)과 Claude Sonnet(`harness-sonnet-worker`)에 맡긴다. 독립적인 작업은 병렬로 진행하고, 각 작업에 담당 파일과 완료 조건을 지정한다. 같은 파일을 여러 작업자가 동시에 수정하지 않는다. Sonnet은 실행 시 선택된 실제 모델을 기록한다.
4. **구현 점검과 테스트**는 Opus 5.5가 독립적으로 수행한다. 변경 내역을 읽고 대상 테스트와 회귀 검증 결과를 확인한다. 실행한 명령, 결과, 남은 위험과 판정을 돌려준다. 문제가 발견되면 담당자가 수정하고 Opus가 다시 점검한다.
5. **최종 검토**는 처음 계획한 Astra가 직접 맡는다. 실제 diff, 테스트 결과, Opus의 판정과 Git 상태를 확인한 뒤 사용자에게 보고한다.

Codex에서는 기본 제공 서브에이전트 도구로 `harness-sol-worker`를 호출한다. Claude 역할은 Claude Code의 `--agent harness-opus-review --model claude-opus-5-5` 또는 `--agent harness-sonnet-worker --model sonnet`으로 호출한다. Claude Code에서는 같은 이름의 사용자 에이전트를 쓸 수 있다. Claude에서 새 Astra 세션을 시작할 때는 `codex exec --model gpt-6.2-astra --json`을 사용하고, 이미 열린 세션은 `codex exec resume <session-id>`로 이어간다. 단계별 요청과 최소 맥락을 표준 입력이나 지원되는 구조화 입력으로 전달한다. 개별 단계를 위임받은 에이전트는 그 단계의 결과를 호출자에게 돌려준다.

인증·권한·모델·도구 상태는 실제 호출 결과로 확인한다. 필수 모델을 사용할 수 없거나 외부 전송이 금지된 경우에는 해당 단계와 이유를 기록하고, 적용되는 프로젝트 예외나 사용자가 승인한 대체 절차를 따른다. 키, 인증 파일, 비공개 자료를 외부 제공자에게 보내지 않는다.
