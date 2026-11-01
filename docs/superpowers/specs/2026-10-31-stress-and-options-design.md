# 반례 탐색·알고리즘 선택지·설계 리뷰 Skill 설계 문서

- 작성일: 2026-10-31
- 선행 문서: `2026-10-30-extra-skills-design.md`

## 1. 확정된 결정

| 항목 | 결정 |
|---|---|
| 새 Skill | `counterexample-hunter`(브루트포스 오라클과 무작위 소형 입력으로 반례 탐색), `algorithm-options`(풀이 후보 2~3개를 표로 제시), `design-review`(응집도·결합도·중복·계층을 `file:line`과 비용으로 보고, 코드는 고치지 않음) |
| 기존 Skill에 합치지 않은 이유 | 트리거 시점이 다르다. 반례 탐색은 예제 통과 뒤, 선택지 제시는 핵심 로직 작성 전이다. `tdd-automator`·`algorithm-optimizer`의 조건에 묶으면 자동 호출 조건이 흐려진다 |
| 선택 방식 | `algorithm-options`는 추천안을 표시하고 사용자가 고를 때까지 코드를 쓰지 않는다. "알아서 골라"라고 하면 추천안을 쓴다 |
| 호출 방식 | `counterexample-hunter`, `algorithm-options`는 조건이 맞으면 자동 호출 |
| 요청 시 호출 | `implementation-review`, `benchmark`, `design-review`는 `agents/openai.yaml`(`allow_implicit_invocation: false`)을 두지 않는다. 그 설정이 있으면 Skill이 모델의 목록에서 빠져 키워드로 부를 수 없기 때문이다. 대신 description을 `Use only when the user invokes $<name> or asks ...`로 시작하고 한국어·영어 키워드를 넣어, 사용자가 요청할 때만 쓰게 한다. 키워드는 문제 지문에 흔히 나오지 않는 말로 고른다(예: '측정', '설명해줘'는 제외) |
| 필수 여부 | `required_skills`에 넣지 않는다. 누락은 PARTIAL이다 |
| description 예산 | 합계 상한을 2000자에서 3000자로 올린다. 초기 설계의 Skill 목록 예산(약 8,000자)보다 여전히 작고, 기존 description을 더 줄이면 트리거 조건이 흐려진다 |

## 2. 연결

- `task-router` 선택 표에 두 줄을 추가한다.
- `algorithm-options`는 허용 복잡도 표를 `../algorithm-optimizer/SKILL.md`에서 가져오고, 브루트포스를 항상 후보에 넣어 `counterexample-hunter`의 오라클로 쓴다.
- `counterexample-hunter`는 반례를 회귀 테스트로 남기고 원인 수정은 `systematic-debugging`에 맡긴다. 임시 폴더 `stress/`는 제출 전에 지운다.
- 두 Skill 모두 결정을 `TASK_BRIEF.md`의 Decision log에 한 줄로 남긴다.

## 3. 검증

- `tests/test_skills.py`의 `EXTRA`, `tests/test_profiles.py`의 `ALL_SKILLS`에 두 Skill을 추가해 기존 검사를 적용한다.
- 새 테스트: `task-router`가 두 Skill을 가리키는지, `algorithm-options`가 대기 규칙과 복잡도 표 링크를 갖는지, `counterexample-hunter`가 시드·브루트포스·회귀 테스트를 언급하는지.
- `test_on_request_policy`: 요청 시 Skill 3개에 `openai.yaml`이 없고 description이 정해진 문장으로 시작하는지 검사한다.
- `codex debug prompt-input`으로 11개가 Skill 목록에 들어가는지 확인한다.
- 수동(사용자): 키워드로 요청 시 Skill이 실제로 쓰이는지, 평소 작업에는 끼어들지 않는지 확인한다.
