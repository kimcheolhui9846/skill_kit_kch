# Windows 11 PowerShell 수동 점검표 (P6-T4)

검토자가 Windows PowerShell 5.1과 PowerShell 7에서 직접 실행하고 결과 칸을 채운다. 2026-11-07에 이 PC(Windows 11 Pro 10.0.26200, 한국어 로캘, 코드 페이지 949)에서 **PowerShell 5.1** 칸은 에이전트가 실행해 "에이전트 실행" 열에 적었다. 이 PC에는 PowerShell 7(`pwsh`)이 없어 7 열은 비어 있다(NOT RUN).

- 실제 `~/.codex`, `~/.claude`를 건드리지 않도록 모든 명령은 임시 폴더와 임시 HOME에서 실행한다(0단계).
- 네트워크를 쓰지 않는다(`--offline`).
- `<KIT>`는 키트를 받은 폴더(예: `D:\aaa\skill_kit_kch`)다.

## 0. 준비 (각 셸에서 한 번)

```powershell
$KIT  = '<KIT>'
$base = Join-Path $env:TEMP ('kitcheck-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$WS   = Join-Path $base '작업 폴더'
$H    = Join-Path $base 'home'
New-Item -ItemType Directory -Force $WS, $H | Out-Null
$env:HOME = $H; $env:USERPROFILE = $H; $env:CODEX_HOME = "$H\.codex"; $env:CLAUDE_CONFIG_DIR = "$H\.claude"
Remove-Item Env:PYTHONUTF8, Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
```

이 준비 블록을 `.ps1` 파일에 저장해 실행한다면, 파일을 **UTF-8 BOM**으로 저장한다. PowerShell 5.1은 BOM이 없는 `.ps1`을 ANSI(cp949)로 읽어서 `'작업 폴더'`가 깨지고 `New-Item`이 "Illegal characters in path"로 실패한다(이 PC에서 재현함). 키트의 `bootstrap.ps1`은 ASCII만 쓰므로 이 문제가 없다(`tests/test_p6_platform.py`가 지킨다). 셸에 직접 붙여 넣는 경우에는 상관없다.

## 1. 점검 항목

| ID | 명령 | 기대 결과 | 에이전트 실행 (PS 5.1, 2026-11-07) | 검토자 PS 5.1 | 검토자 PS 7 |
|---|---|---|---|---|---|
| W-01 환경 | `$PSVersionTable.PSVersion; [Console]::OutputEncoding.WebName; chcp; python -c "import sys,locale;print(sys.version.split()[0], locale.getpreferredencoding(False), sys.stdout.encoding)"` | 버전과 인코딩이 나온다. 한국어 기본값은 콘솔 `ks_c_5601-1987`(cp949), 코드 페이지 949, Python preferred `cp949`. PS 7은 `$OutputEncoding`이 utf-8 | 5.1.26100.9711, 949, Python 3.12.10, preferred cp949, stdout cp949 | | |
| W-02 도움말 | `powershell -NoProfile -ExecutionPolicy Bypass -File "$KIT\bootstrap.ps1" --help; $LASTEXITCODE` (PS 7: `pwsh -NoProfile -File …`) | 사용법이 나오고 0 | 자동 테스트 `tests/test_entrypoints.py`(PowerShell 23개)가 같은 명령을 실행해 통과 | | |
| W-03 실행 정책 | 기본 정책에서 `& "$KIT\bootstrap.ps1" --help` | 정책이 `Restricted`이면 "running scripts is disabled" 오류. `-ExecutionPolicy Bypass`(그 프로세스만)로는 실행된다. 전역 정책은 바꾸지 않는다 | 확인하지 않음 | | |
| W-04 설치 | `Push-Location $WS; python "$KIT\run_kit.py" install --agent both --offline; $LASTEXITCODE; Pop-Location` | `Status: READY`, 0. 공백·한글 경로에서도 같다 | READY, 0 | | |
| W-05 검증 | `python "$KIT\run_kit.py" verify --agent both --offline --target $WS; $LASTEXITCODE` | READY, 0 | READY, 0 | | |
| W-06 기존 설치기 | `Push-Location $WS; powershell -NoProfile -ExecutionPolicy Bypass -File "$KIT\bootstrap.ps1" --offline; $LASTEXITCODE; Pop-Location` | READY, 0 | READY, 0 | | |
| W-07 cp949 콘솔의 한글 | `python "$KIT\run_kit.py" task add T-1 --title ('한글 ' + [char]0x2014 + ' 끝') --target $WS; python "$KIT\run_kit.py" task list --target $WS` | 오류 없이 0. 한글은 그대로 보이고, cp949에 없는 문자(—, 이모지)는 `?`로 보인다(출력만, 키트가 `errors=replace`로 바꿈) | 0, 0. 한글 출력, —와 😀는 `?` | | |
| W-08 파일에는 원래 값 | `[IO.File]::ReadAllText("$WS\.kit\work\tasks.json", [Text.Encoding]::UTF8).Contains([char]0x2014)` | `True`(작업 파일은 항상 UTF-8, 원래 문자 그대로) | True | | |
| W-09 JSON 파이프 | `python "$KIT\run_kit.py" task list --json --target $WS \| ConvertFrom-Json \| Select-Object -ExpandProperty tasks \| Select-Object id, title` | 유효한 JSON. 제목의 한글은 그대로, cp949에 없는 문자는 `?`. PS 7도 같다(PS 7은 외부 프로그램 출력을 `[Console]::OutputEncoding`으로 읽음) | ASCII 제목으로 `ConvertFrom-Json` 성공(id, title 표시). 한글 제목의 파이프는 확인하지 않음 | | |
| W-10 UTF-8 모드 | `$env:PYTHONUTF8 = '1'; python "$KIT\run_kit.py" task list --target $WS; Remove-Item Env:PYTHONUTF8` | 콘솔이 cp949면 한글이 깨져 보일 수 있다. 정확한 문자가 필요하면 `chcp 65001` 또는 Windows Terminal(UTF-8)을 쓴다 | 확인하지 않음 | | |
| W-11 리디렉션 | `python "$KIT\run_kit.py" task list --target $WS > "$base\out.txt"; Format-Hex "$base\out.txt" \| Select-Object -First 2` | 설정을 바꾸지 않은 PS 5.1의 `>`는 UTF-16LE(BOM `FF FE`), PS 7은 BOM 없는 UTF-8로 저장한다. 프로필에서 `$PSDefaultParameterValues['Out-File:Encoding']`을 바꿨다면 그 인코딩이다. 어느 쪽이든 키트는 0 | exit 0. 에이전트 도구의 PowerShell은 기본값이 바뀌어 있어 UTF-8 BOM(`EF BB BF`)으로 저장됨. 기본 설정의 PS 5.1 결과가 아님 | | |
| W-12 제거 | `python "$KIT\run_kit.py" uninstall --agent both --target $WS; $LASTEXITCODE` | READY, 0. 키트가 쓴 파일만 지운다 | READY, 0 | | |
| W-13 HOME 무변경 | `(Get-ChildItem -Recurse -File $H -ErrorAction SilentlyContinue \| Measure-Object).Count` | 0 | 0 | | |
| W-14 정리 | `Remove-Item -Recurse -Force $base` | 임시 폴더만 지운다 | 지움 | | |

## 2. 판정

- 모든 행이 기대 결과와 같으면 PASS다.
- W-07~W-11의 `?` 표시와 인코딩 차이는 콘솔 설정 때문이고 키트 결함이 아니다. 다만 키트가 오류로 멈추거나(종료 코드 ≠ 0), JSON이 깨지거나, `tasks.json`의 값이 바뀌면 결함이다.
- PowerShell 7 열이 비어 있으면 PS 7은 `UNVERIFIED`다.

| 셸 | 검토자 | 날짜 | 판정 | 메모 |
|---|---|---|---|---|
| Windows PowerShell 5.1 | | | | |
| PowerShell 7 | | | | |
