# mixpanel-cli

**Agent-native Mixpanel CLI** — 모든 출력을 JSON으로 반환하는 AI 에이전트 친화적 분석 도구.

자연어 쿼리(`ask`), 대화형 REPL(`shell`), 임계값 모니터링(`watch`), Raw 데이터 Export까지 하나의 CLI로 처리합니다.

---

## 목차

- [설치](#설치)
- [인증 설정](#인증-설정)
- [빠른 시작](#빠른-시작)
- [전역 플래그](#전역-플래그)
- [명령 레퍼런스](#명령-레퍼런스)
  - [analytics](#analytics)
  - [events](#events)
  - [export](#export)
  - [ask (AI 쿼리)](#ask-ai-쿼리)
  - [watch (모니터링)](#watch-모니터링)
  - [shell (REPL)](#shell-repl)
  - [dashboard / lexicon](#dashboard--lexicon-비공식-api)
  - [config](#config)
  - [project](#project)
- [출력 형식](#출력-형식)
- [파이프라인 활용](#파이프라인-활용)
- [에러 코드](#에러-코드)
- [개발 가이드](#개발-가이드)

---

## mixpanel-cli vs Mixpanel MCP

AI 에이전트에서 Mixpanel 데이터를 다루는 두 가지 방법을 비교합니다.

| 항목 | **mixpanel-cli** | **Mixpanel MCP** |
|---|---|---|
| **통합 방식** | CLI — 어느 환경에서든 `subprocess` 호출 | MCP 프로토콜 — Claude Code 등 MCP 지원 클라이언트 전용 |
| **인증 관리** | 환경변수 / OS keychain / 프로파일 | MCP 서버 설정 파일에 직접 기재 |
| **출력 형식** | 항상 구조화된 JSON (파싱 보장) | 자연어 텍스트 (파싱 불안정) |
| **파이프라인** | `--quiet` + `jq` 로 직접 처리 가능 | 불가 (에이전트 내부 처리만) |
| **AI 쿼리** | `ask query` — Claude가 API 파라미터로 변환 후 실행 | MCP 툴 호출로 처리 |
| **모니터링** | `watch start` — 임계값 알림 + webhook 내장 | 없음 |
| **REPL 모드** | `shell start` — 대화형 세션 | 없음 |
| **Raw Export** | JSONL 스트리밍, 30일 자동 청킹 | 없음 |
| **다중 리전** | `--region us\|eu\|in` 플래그 | 서버 설정에 의존 |
| **다중 프로파일** | dev/staging/prod 분리 관리 | 단일 설정 |
| **에러 처리** | 모든 에러를 JSON으로 반환 (exit 0) | 에러 메시지가 텍스트로 반환됨 |
| **CI/CD 통합** | 스크립트에서 직접 호출 가능 | MCP 클라이언트 필요 |
| **오프라인 사용** | 가능 (--dry-run) | 불가 |
| **설치** | `pip install mixpanel-cli` | MCP 서버 별도 설치 + 클라이언트 설정 |

### 언제 mixpanel-cli를 쓸까?

- **자동화 스크립트** — cron, GitHub Actions, 데이터 파이프라인
- **에이전트 도구** — Claude/GPT 에이전트가 subprocess로 호출
- **터미널 워크플로우** — 개발자가 직접 데이터 탐색
- **구조화된 데이터 필요** — jq, Python으로 응답을 파싱해서 처리
- **모니터링** — watch + webhook으로 지표 이상 탐지

### 언제 Mixpanel MCP를 쓸까?

- **Claude Code 내 대화형 분석** — 채팅으로 데이터를 탐색할 때
- **빠른 탐색** — 설치/설정 없이 즉시 사용
- **자연어 우선** — 파싱 없이 텍스트 답변만 필요할 때

---

## 설치

```bash
# 기본 (analytics, events, export, watch, shell)
pip install mixpanel-cli

# AI 자연어 쿼리 포함 (ask 명령)
pip install mixpanel-cli[ai]

# REPL 모드 포함 (shell 명령)
pip install mixpanel-cli[shell]

# 전부
pip install mixpanel-cli[all]
```

> **Python 3.11 이상** 필요.

---

## 인증 설정

### 방법 1: 환경변수 (권장)

```bash
export MIXPANEL_USERNAME="your-email@company.com"
export MIXPANEL_SECRET="your-service-account-secret"
export MIXPANEL_PROJECT_ID="123456"
```

### 방법 2: 프로파일 설정 (keychain 저장)

```bash
mixpanel config set \
  --username "your-email@company.com" \
  --secret "your-service-account-secret" \
  --project-id "123456"
```

자격증명은 OS keychain(macOS Keychain / Linux Secret Service)에 안전하게 저장됩니다.

### 방법 3: 명령줄 플래그

```bash
mixpanel --project-id 123456 analytics insight --event "Sign Up" \
  --from-date 2026-03-01 --to-date 2026-03-31
```

### 인증 우선순위

`CLI 플래그` > `환경변수` > `프로파일(keychain)`

---

## 빠른 시작

```bash
# 이벤트 카운트 조회
mixpanel analytics insight --event "Sign Up" \
  --from-date 2026-03-01 --to-date 2026-03-31

# AI 자연어 쿼리
mixpanel ask query "이번 달 Sign Up 이벤트 몇 건이야?"

# 이벤트 목록 보기
mixpanel events list

# Raw 데이터 파일로 저장
mixpanel export events \
  --from-date 2026-03-01 --to-date 2026-03-31 \
  --event-name "Purchase" --file purchases.jsonl

# 대화형 REPL
mixpanel shell start
```

---

## 전역 플래그

모든 명령에 사용 가능. **서브커맨드 이전**에 위치해야 합니다.

```bash
mixpanel [전역 플래그] <명령> [명령 옵션]
```

| 플래그 | 설명 |
|---|---|
| `--profile TEXT` | 사용할 인증 프로파일 (기본: `default`) |
| `--project-id TEXT` | 프로젝트 ID 오버라이드 |
| `--region [us\|eu\|in]` | 데이터 리전 (기본: `us`) |
| `--pretty` | JSON 들여쓰기 출력 |
| `--quiet` | `data` 값만 출력 (파이프라인용) |
| `--debug` | HTTP 요청/응답 디버그 정보 출력 |
| `--no-color` | 컬러 출력 비활성화 |
| `--timeout INTEGER` | HTTP 타임아웃 초 (기본: `30`) |

```bash
# EU 리전, pretty print
mixpanel --region eu --pretty analytics insight --event "Login" \
  --from-date 2026-03-01 --to-date 2026-03-31

# 파이프라인용 data만 출력
mixpanel --quiet analytics insight --event "Sign Up" \
  --from-date 2026-03-01 --to-date 2026-03-31 | jq '.data.values'
```

---

## 명령 레퍼런스

### analytics

이벤트 카운트, 퍼널, 리텐션, 플로우 분석.

#### `analytics insight` — 이벤트 시계열

```bash
mixpanel analytics insight \
  --event "Sign Up" \
  --from-date 2026-03-01 \
  --to-date 2026-03-31 \
  [--unit day|week|month]   # 기본: day
```

```json
{
  "status": "ok",
  "data": {
    "data": {
      "series": ["2026-03-01", "2026-03-02"],
      "values": { "Sign Up": { "2026-03-01": 120, "2026-03-02": 135 } }
    }
  },
  "meta": { "event": "Sign Up", "unit": "day" }
}
```

#### `analytics funnel` — 퍼널 분석

```bash
mixpanel analytics funnel \
  --id 12345 \
  --from-date 2026-03-01 \
  --to-date 2026-03-31
```

#### `analytics retention` — 리텐션 분석

```bash
mixpanel analytics retention \
  --event "Sign Up" \
  --from-date 2026-03-01 \
  --to-date 2026-03-31 \
  [--unit day|week]   # 기본: day
```

#### `analytics flow` — 플로우 분석

```bash
mixpanel analytics flow \
  --event "Purchase" \
  --from-date 2026-03-01 \
  --to-date 2026-03-31
```

---

### events

이벤트 목록 및 속성 조회.

#### `events list` — 이벤트 목록

```bash
mixpanel events list \
  [--search "Sign"]     # 이름 필터
  [--limit 100]         # 최대 결과 수 (기본: 255)
  [--page 1]            # 페이지 번호 (페이지당 50개)
```

```bash
# 이름에 "Purchase" 포함된 이벤트만
mixpanel --quiet events list --search "Purchase"
# → ["Purchase", "Purchase Complete", "Purchase Failed"]
```

#### `events properties` — 이벤트 속성 목록

```bash
mixpanel events properties --event "Purchase"
```

---

### export

Raw 이벤트 데이터를 JSONL 형식으로 내보내기. **30일 단위 자동 청킹**.

```bash
mixpanel export events \
  --from-date 2026-03-01 \
  --to-date 2026-03-31 \
  [--event-name "Purchase"]    # 특정 이벤트만 필터
  [--file events.jsonl]        # 파일 저장 (없으면 stdout 스트리밍)
  [--timeout 120]              # 대용량 데이터용 타임아웃 조정
```

```bash
# stdout으로 스트리밍 → 직접 처리
mixpanel export events \
  --from-date 2026-01-01 --to-date 2026-03-31 \
  --event-name "Purchase" | jq '.properties.amount' | awk '{sum+=$1} END {print sum}'
```

> 30일 초과 범위는 자동으로 청킹하여 순차 요청합니다.

---

### ask (AI 쿼리)

> `pip install mixpanel-cli[ai]` 및 `ANTHROPIC_API_KEY` 필요.

자연어로 Mixpanel 데이터를 조회합니다. Claude가 쿼리를 분석해 적절한 API를 자동으로 호출합니다.

#### `ask query`

```bash
mixpanel ask query "이번 달 Sign Up 몇 건이야?"
mixpanel ask query "지난 주 Purchase 이벤트 퍼널 전환율"
mixpanel ask query "3월 Login 리텐션 분석해줘"
```

**플래그:**

| 플래그 | 설명 |
|---|---|
| `--dry-run` | API 실행 없이 변환된 파라미터만 반환 |
| `--explain` | 응답 meta에 AI 해설 포함 |
| `--no-summary` | 자연어 요약 생략 |

```bash
# 어떤 API 파라미터로 변환되는지 확인
mixpanel ask query "Sign Up 분석" --dry-run
```

```json
{
  "status": "ok",
  "data": {
    "command": "insight",
    "params": {
      "event": "Sign Up",
      "from_date": "2026-03-01",
      "to_date": "2026-03-31",
      "unit": "day"
    }
  }
}
```

```bash
# AI 해설 포함
mixpanel ask query "Login 트렌드" --explain
```

---

### watch (모니터링)

이벤트 지표를 주기적으로 조회하고 임계값 초과 시 알림을 발송합니다.

#### `watch start`

```bash
mixpanel watch start \
  --event "Purchase" \
  --from-date 2026-03-01 \
  --to-date 2026-03-31 \
  [--interval 60]              # 폴링 간격 분 (기본: 60)
  [--threshold-drop 20]        # 이전 대비 20% 이상 하락 시 알림
  [--threshold-rise 50]        # 이전 대비 50% 이상 상승 시 알림
  [--webhook "https://..."]    # Slack/Discord 웹훅 URL
```

```bash
# Purchase 20% 하락 시 Slack 알림
mixpanel watch start \
  --event "Purchase" \
  --from-date 2026-03-01 --to-date 2026-03-31 \
  --threshold-drop 20 \
  --webhook "https://hooks.slack.com/services/..."
```

알림 예시 (stderr):
```
[ALERT] Purchase -25.3% 하락 (임계값: -20%)
```

Ctrl+C로 종료.

---

### shell (REPL)

> `pip install mixpanel-cli[shell]` 필요.

대화형 REPL 모드. 반복 인증/설정 없이 여러 쿼리를 연속 실행합니다.

```bash
mixpanel shell start [--project-id 123456] [--region eu]
```

```
mixpanel> analytics insight --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-31
mixpanel> use project 999999
mixpanel> events list
mixpanel> exit
```

**REPL 내장 명령:**

| 명령 | 설명 |
|---|---|
| `use project <id>` | 활성 프로젝트 변경 |
| `exit` / `quit` | 종료 |

---

### dashboard / lexicon (비공식 API)

> **비공식 API 사용.** Mixpanel 업데이트 시 동작이 변경될 수 있습니다.
> 실행 시 stderr에 `[WARNING]` 메시지가 출력됩니다.

#### dashboard

```bash
mixpanel dashboard list                     # 대시보드 목록
mixpanel dashboard get --id 12345           # 특정 대시보드
mixpanel dashboard create --title "KPI"     # 새 대시보드
mixpanel dashboard update --id 12345 --title "KPI v2"
mixpanel dashboard delete --id 12345
```

#### lexicon

```bash
mixpanel lexicon list                                    # 이벤트 목록
mixpanel lexicon edit-event --name "Purchase" \
  --description "구매 완료 이벤트" --status active      # 이벤트 메타 수정
mixpanel lexicon edit-property \
  --event "Purchase" --property "amount" \
  --description "결제 금액 (USD)"                        # 프로퍼티 메타 수정
```

---

### config

인증 프로파일 관리.

```bash
mixpanel config set \
  --username "user@company.com" \
  --secret "svc-account-secret" \
  --project-id "123456" \
  [--profile staging]    # 이름 있는 프로파일

mixpanel config get                  # 현재 프로파일 정보 확인
mixpanel config list                 # 프로파일 목록
```

여러 환경(dev/staging/prod) 관리:

```bash
# 설정
mixpanel config set --profile prod --project-id 111 --secret "..."
mixpanel config set --profile staging --project-id 222 --secret "..."

# 사용
mixpanel --profile prod analytics insight --event "Sign Up" ...
mixpanel --profile staging events list
```

---

### project

```bash
mixpanel project list    # 접근 가능한 프로젝트 목록
mixpanel project info    # 현재 프로젝트 정보
```

---

## 출력 형식

모든 명령은 **stdout에 JSON만 출력**합니다.

### 성공 응답

```json
{
  "status": "ok",
  "data": { ... },
  "meta": { ... }
}
```

### 에러 응답

```json
{
  "status": "error",
  "code": "AUTH_ERROR",
  "message": "HTTP 401: unauthorized"
}
```

### `--quiet` 모드

`data` 값만 출력합니다. jq 파이프라인에 최적화됩니다.

```bash
# 전체 응답
mixpanel analytics insight --event "Sign Up" ...
# → {"status": "ok", "data": {...}, "meta": {...}}

# quiet: data만
mixpanel --quiet analytics insight --event "Sign Up" ...
# → {"data": {...}, "series": [...], "values": {...}}
```

### `--pretty` 모드

들여쓰기된 JSON 출력. 사람이 읽기 편한 형식.

---

## 파이프라인 활용

`--quiet` + `jq` 조합으로 데이터를 바로 처리합니다.

```bash
# 특정 날짜의 Sign Up 수 추출
mixpanel --quiet analytics insight \
  --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-31 \
  | jq '.data.values["Sign Up"]["2026-03-15"]'

# 이벤트 목록을 배열로 받아 반복 처리
mixpanel --quiet events list | jq '.[]' -r | while read event; do
  echo "Processing: $event"
done

# Purchase 데이터를 CSV로 변환
mixpanel export events \
  --from-date 2026-03-01 --to-date 2026-03-31 \
  --event-name "Purchase" \
  | jq -r '[.properties.amount, .properties.country] | @csv'

# 에러 체크 후 진행
result=$(mixpanel --quiet analytics insight --event "Sign Up" ...)
if echo "$result" | jq -e '.status == "error"' > /dev/null; then
  echo "Error: $(echo $result | jq -r '.message')" >&2
  exit 1
fi
```

### AI 에이전트 통합

모든 응답이 구조화된 JSON이므로 AI 에이전트가 파싱하기 쉽습니다.

```python
import subprocess, json

result = subprocess.run(
    ["mixpanel", "--quiet", "analytics", "insight",
     "--event", "Sign Up", "--from-date", "2026-03-01", "--to-date", "2026-03-31"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
values = data["data"]["values"]["Sign Up"]
```

---

## 에러 코드

| 코드 | HTTP | 설명 |
|---|---|---|
| `AUTH_ERROR` | 401 | 인증 실패 |
| `PERMISSION_ERROR` | 403 | 권한 없음 |
| `NOT_FOUND` | 404 | 리소스 없음 |
| `RATE_LIMIT` | 429 | 요청 한도 초과 (자동 재시도 후) |
| `QUERY_ERROR` | 400 | 잘못된 쿼리 파라미터 |
| `SERVER_ERROR` | 500/503 | Mixpanel 서버 오류 |
| `AI_NOT_INSTALLED` | — | `anthropic` 패키지 미설치 |
| `AI_PARSE_ERROR` | — | AI 응답 파싱 실패 |
| `PROFILE_NOT_FOUND` | — | 지정한 프로파일 없음 |
| `API_CHANGED` | — | 비공식 API 응답 구조 변경 감지 |

---

## 개발 가이드

```bash
# 개발 환경 설치
uv pip install --system -e ".[dev,ai,shell]"
# 또는
pip install -e ".[dev,ai,shell]"

# 전체 테스트
python3 -m pytest tests/ -v

# 특정 테스트만
python3 -m pytest tests/unit/test_analytics.py -v
python3 -m pytest tests/e2e/test_scenarios.py -v
python3 -m pytest tests/e2e/test_edge_cases.py -v

# 커버리지 확인
python3 -m pytest tests/ --cov=mixpanel_cli --cov-report=term-missing
```

### 프로젝트 구조

```
mixpanel_cli/
├── main.py              # CLI 진입점, 전역 플래그, AppContext
├── commands/
│   ├── analytics.py     # insight / funnel / retention / flow
│   ├── events.py        # list / properties
│   ├── export.py        # events (JSONL export, 30일 청킹)
│   ├── ask.py           # AI 자연어 쿼리
│   ├── watch.py         # 폴링 모니터링
│   ├── shell.py         # 대화형 REPL
│   ├── dashboard.py     # 비공식 API
│   ├── lexicon.py       # 비공식 API
│   ├── config.py        # 프로파일 관리
│   └── _utils.py        # make_client() 헬퍼
├── client/
│   ├── base.py          # HTTP 클라이언트 (retry, auth)
│   ├── mixpanel.py      # Mixpanel API 메서드
│   └── claude.py        # Anthropic Claude 클라이언트
├── auth/
│   ├── profile.py       # AuthContext, 인증 우선순위
│   └── keychain.py      # OS keychain 연동
├── models.py            # CLIResponse, Profile 모델
├── exceptions.py        # 에러 계층, HTTP_STATUS_TO_ERROR
├── output/
│   └── formatter.py     # JSON 직렬화 + 출력
└── types.py             # Click DATE 파라미터 타입
```

### 새 명령 추가

```python
# 1. mixpanel_cli/commands/new_cmd.py
import click
from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error
from mixpanel_cli.exceptions import MixpanelCLIError

@click.group("new-cmd")
def new_cmd_group():
    """새 명령 그룹."""
    pass

@new_cmd_group.command("action")
@click.option("--param", required=True, help="파라미터")
@click.pass_context
def action(ctx, param):
    obj = ctx.obj
    try:
        client, _ = make_client(obj)
        data = client.some_method(param)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=obj.pretty, quiet=obj.quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=obj.pretty)

# 2. mixpanel_cli/main.py에 등록
# from mixpanel_cli.commands import new_cmd
# cli.add_command(new_cmd.new_cmd_group, name="new-cmd")
```

---

## 라이선스

MIT
