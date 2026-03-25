# mixpanel-cli PRD

**버전:** 1.1 (Architect + Critic 검토 반영)
**작성일:** 2026-03-26
**전략:** Option C (AI-Powered Analytics CLI) — Phase 1a → 1b → 2 단계 빌드
**구현 언어:** Python 3.11+ / Click
**설계 원칙:** CLI-Anything 핵심 패턴 차용 (JSON 출력, REPL 모드, SKILL.md)

---

## 1. 문제 정의 및 목표

### 문제
- Mixpanel MCP는 대화형 세션에서만 동작하며, 배치 작업·파이프라인·스크립트에서 사용 불가
- 에이전트(Claude Code 등)가 Mixpanel 데이터를 활용하려면 매번 MCP 연결·OAuth 흐름이 필요해 자동화 불가
- 멀티 프로젝트/멀티 리전 작업 시 컨텍스트 전환 비용이 높음
- 분석 결과를 다른 도구(jq, awk, CI 파이프라인)와 조합하기 어려움
- Mixpanel 쿼리 문법을 모르는 에이전트는 올바른 API 파라미터를 추측해야 함

### 목표
1. 에이전트가 자연어 한 줄로 Mixpanel 분석을 완료할 수 있는 CLI 제공
2. 모든 출력이 JSON 구조화 데이터로 제공되어 파이프라인 조합 가능
3. Service Account 기반 무인 인증으로 CI/자동화 환경에서 완전 동작

---

## 2. 타겟 유저 및 페르소나

### 페르소나 1: Claude Code 에이전트
- **배경:** 코드 작업 중 사용자 행동 데이터가 필요한 AI 에이전트
- **니즈:** "지난 7일 신규 가입자 수를 뽑아서 분석에 써야 함"
- **행동 패턴:** SKILL.md를 읽고 CLI 명령어를 조합해 결과를 JSON으로 파싱
- **Pain Points:** MCP는 대화 세션에 종속, API 직접 호출은 인증·파라미터 처리 복잡

### 페르소나 2: 데이터 엔지니어 / PM
- **배경:** 터미널에 익숙한 실무자, 매일 Mixpanel 대시보드를 반복 확인
- **니즈:** 스크립트로 주간 리포트 자동화, Slack 알림과 연동
- **행동 패턴:** cron + mixpanel-cli로 파이프라인 구성
- **Pain Points:** Mixpanel 웹 UI는 반복 작업에 비효율적

### 페르소나 3: 시니어 개발자 (디버깅/검증)
- **배경:** 프로덕션 이슈 발생 시 이벤트 데이터를 빠르게 확인해야 함
- **니즈:** REPL 모드에서 즉석 쿼리, 결과 탐색
- **Pain Points:** Mixpanel UI 로딩 느림, 쿼리 재사용 불가

---

## 3. User Stories

### US-001: Service Account 인증 설정
**As a** 데이터 엔지니어
**I want to** `mixpanel config init`으로 프로파일을 설정하고
**So that** 이후 모든 명령에서 인증을 반복하지 않아도 됨

**Acceptance Criteria:**
- [ ] `mixpanel config init --profile prod` 실행 시 service_account_username, service_account_secret, project_id, region 입력 프롬프트 제공
- [ ] Secret은 OS keychain에만 저장 (`keyring` 라이브러리); 프로파일 메타(username, project_id, region)는 `~/.mixpanel/profiles.json`에 평문 저장
- [ ] `--profile` 미지정 시 `default` 프로파일 자동 사용
- [ ] `mixpanel config list`로 프로파일 목록 출력 (secret 미포함)
- [ ] 연결 테스트: `GET /api/2.0/projects` 호출로 인증 확인

### US-002: Insights 쿼리 실행
**As a** Claude Code 에이전트
**I want to** `mixpanel analytics insight --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-26`을 실행하고
**So that** JSON으로 이벤트 카운트를 받아 후속 분석에 사용

**Acceptance Criteria:**
- [ ] 결과가 `{"status": "ok", "data": {...}, "meta": {"query_time_ms": 120}}` 형태로 출력
- [ ] `--format csv` 옵션 시 CSV 형태로 출력 (전역 `--output` 과 분리)
- [ ] `--quiet` 옵션 시 `data` 값만 raw JSON 출력 (jq 파이프 친화)
- [ ] 쿼리 실패 시 `{"status": "error", "code": "QUERY_ERROR", "message": "..."}` 반환

### US-003: 자연어 쿼리 (AI 모드)
**As a** Claude Code 에이전트
**I want to** `mixpanel ask "지난 30일 동안 결제 완료 이벤트가 가장 많이 발생한 날은?"`을 실행하고
**So that** Mixpanel 쿼리 문법 없이도 올바른 분석 결과를 받음

**Acceptance Criteria:**
- [ ] Claude API를 통해 자연어 → Mixpanel 쿼리 파라미터 변환 (1회 호출로 파라미터 생성 + 요약 템플릿 동시 생성)
- [ ] 이벤트 목록을 TTL 1시간 캐시 (`~/.mixpanel/cache/events_{project_id}.json`) — 반복 호출 레이턴시 감소
- [ ] 실제 API 호출 후 결과를 자연어 요약과 함께 반환
- [ ] `--dry-run` 옵션 시 실제 API 호출 없이 생성된 쿼리 파라미터만 출력 (검증 가능)
- [ ] `--explain` 옵션 시 쿼리 구성 이유를 함께 출력
- [ ] `--no-summary` 옵션 시 자연어 요약 없이 raw 데이터만 반환
- [ ] `anthropic` 패키지 미설치 시: `{"status": "error", "code": "AI_NOT_INSTALLED", "message": "pip install mixpanel-cli[ai]"}`

### US-004: 대시보드 관리
**As a** PM
**I want to** `mixpanel dashboard list`와 `mixpanel dashboard get --id <id>`를 실행하고
**So that** CI 파이프라인에서 대시보드 상태를 자동으로 확인하고 슬랙에 전달

**Acceptance Criteria:**
- [ ] `dashboard list`가 `[{"id": "...", "name": "...", "created_at": "..."}]` 반환
- [ ] `dashboard create --from-file spec.json`으로 대시보드 생성
- [ ] `dashboard duplicate --id <id> --name "복사본"` 지원
- [ ] 비공식 API 응답 스키마 변경 시 `{"status": "error", "code": "API_CHANGED", "message": "Dashboard API response format changed. This command uses an undocumented API."}` 반환
- [ ] 첫 사용 시 stderr에 경고: `[WARNING] dashboard commands use an undocumented API that may change without notice`

### US-005: REPL 대화형 모드
**As a** 개발자
**I want to** `mixpanel shell`을 실행해 대화형 환경에서 쿼리를 탐색하고
**So that** 매번 전체 명령어를 타이핑하지 않아도 컨텍스트를 유지하며 분석

**Acceptance Criteria:**
- [ ] `mixpanel shell` 진입 시 현재 프로파일/프로젝트 정보 표시
- [ ] `use project <id>` 명령으로 프로젝트 전환
- [ ] `history` 명령으로 이전 쿼리 조회
- [ ] `exit` 또는 Ctrl+D로 종료
- [ ] `prompt-toolkit` 미설치 시: `pip install mixpanel-cli[shell]` 안내

### US-006: 이벤트 데이터 Export
**As a** 데이터 엔지니어
**I want to** `mixpanel export events --from-date 2026-03-01 --to-date 2026-03-26 --file events.jsonl`을 실행하고
**So that** Raw 이벤트 데이터를 로컬에 저장해 다른 분석 도구로 처리

**Acceptance Criteria:**
- [ ] JSONL 형식으로 스트리밍 저장 (대용량 처리)
- [ ] `--event-name` 필터로 특정 이벤트만 추출
- [ ] 30일 초과 기간 요청 시 자동으로 30일 단위 청킹 후 병합
- [ ] 진행 상황을 stderr로 출력 (stdout은 데이터만)
- [ ] HTTP 타임아웃: 기본 30초, `--timeout` 옵션으로 조정 가능

### US-007: 이상 감지 자동 알림 (Phase 2)
**As a** PM
**I want to** `mixpanel watch --metric "Sign Up" --threshold-drop 20`을 실행하고
**So that** 핵심 메트릭이 20% 이상 하락하면 즉시 알림

**Acceptance Criteria:**
- [ ] 지정 주기(기본 1시간)로 메트릭 폴링 (foreground blocking 프로세스)
- [ ] 하락/상승 임계값 설정 가능
- [ ] `--webhook <url>`으로 알림 전송 (JSON POST)
- [ ] Ctrl+C로 안전하게 종료

---

## 4. 상세 유저 플로우

### 플로우 1: 초기 설정 (에이전트 또는 사람)

**단계 1: 설치**
```bash
# Phase 1 (기본 CLI)
pip install mixpanel-cli

# Phase 2 포함 (AI 기능)
pip install mixpanel-cli[ai,shell]

# 전체
pip install mixpanel-cli[all]
```

**단계 2: 프로파일 초기화**
```bash
mixpanel config init
```
- `service_account_username` 입력 요청
- `service_account_secret` 입력 요청 (echo 비활성화) → OS keychain에 저장
- `project_id` 입력 요청
- `region` 선택: `[us|eu|in]` (기본: us)
- `~/.mixpanel/profiles.json` 생성 (secret 미포함)
- 연결 테스트 후: `{"status": "ok", "profile": "default", "project_id": "123456"}`

**CI/에이전트 환경 (환경변수 방식)**
```bash
export MIXPANEL_USERNAME="svc-account@123456.mixpanel.com"
export MIXPANEL_SECRET="your-secret"
export MIXPANEL_PROJECT_ID="123456"
# config init 불필요
mixpanel project info
```

---

### 플로우 2: 에이전트 분석 플로우 (핵심)

**에이전트 명령:** `mixpanel ask "지난 7일 신규 가입 이벤트 트렌드"`

1. 캐시 확인: `~/.mixpanel/cache/events_{project_id}.json` (TTL 1시간)
   - 캐시 유효: 캐시된 이벤트 목록 사용
   - 캐시 만료: Mixpanel API로 이벤트 목록 수집 후 캐시 업데이트
2. Claude API 호출 1회: 자연어 → Query 파라미터 + 요약 템플릿 동시 생성
   ```json
   {
     "query": {"type": "insights", "event": "Sign Up", "from_date": "2026-03-19", "to_date": "2026-03-26", "unit": "day"},
     "summary_template": "지난 7일간 신규 가입은 총 {total}건이며, {peak_date}에 피크({peak_count}건)를 기록했습니다."
   }
   ```
3. `--dry-run` 이면 파라미터만 출력 후 종료
4. Mixpanel Query API 호출
5. 요약 템플릿에 값 채워 반환:
   ```json
   {
     "status": "ok",
     "summary": "지난 7일간 신규 가입은 총 1,234건이며...",
     "data": {"2026-03-19": 142, ...},
     "query_used": {...}
   }
   ```

---

### 플로우 3: REPL 세션

```
$ mixpanel shell
Mixpanel CLI v1.0.0
Profile: default | Project: My App (123456) | Region: US

mixpanel> events list --limit 10
mixpanel> analytics insight --event "Purchase" --from-date 2026-03-01
mixpanel> use project 789012
Switched to project: My App Staging (789012)
mixpanel> history
mixpanel> exit
```

---

## 5. Functional Requirements

### 5.1 커맨드 구조

```
mixpanel [GLOBAL_OPTIONS] COMMAND [ARGS]

├── config
│   ├── init    [--profile <name>] [--region us|eu|in]
│   ├── list
│   ├── show    [--profile <name>]
│   ├── set     --profile <name> --key <field> --value <value>
│   └── delete  --profile <name>
│
├── project
│   ├── info    [--project-id <id>]
│   └── list
│
├── analytics
│   ├── insight   --event <name> --from-date <date> --to-date <date>
│   │             [--unit day|week|month] [--format json|csv|table]
│   ├── funnel    --id <funnel-id> --from-date <date> --to-date <date>
│   ├── retention --event <name> --from-date <date> --to-date <date> [--unit day|week]
│   └── flow      --event <name> --from-date <date> --to-date <date>
│
├── events
│   ├── list        [--limit <n>] [--search <keyword>] [--page <n>]
│   ├── get         --name <event-name>
│   └── properties  --event <name>
│
├── dashboard           [Phase 1b — 비공식 API, 경고 포함]
│   ├── list
│   ├── get         --id <id>
│   ├── create      --name <name> [--from-file <spec.json>]
│   ├── update      --id <id> --from-file <spec.json>
│   ├── duplicate   --id <id> --name <new-name>
│   └── delete      --id <id>
│
├── export
│   └── events    --from-date <date> --to-date <date>
│                 [--event-name <name>] [--file <path>]
│                 [--timeout <seconds>]
│
├── lexicon         [Phase 1b — 비공식 API, 경고 포함]
│   ├── list
│   ├── edit-event    --name <name> --description <desc> [--hidden]
│   └── edit-property --event <name> --property <name> --description <desc>
│
├── ask     "<natural language query>"
│           [--dry-run] [--explain] [--no-summary]
│           [--refresh-cache]
│
├── watch   --metric <event>
│           [--threshold-drop <pct>] [--threshold-rise <pct>]
│           [--interval <minutes>] [--webhook <url>]
│
└── shell                                         [Phase 2]
```

**구현 노트: Python 예약어 `from` 처리**
```python
# Click에서 --from 플래그는 Python 예약어라 변수명 remapping 필수:
@click.option('--from-date', 'from_date', required=True, help='시작 날짜 (YYYY-MM-DD)')
@click.option('--to-date', 'to_date', required=True, help='종료 날짜 (YYYY-MM-DD)')
```
사용자 인터페이스는 `--from-date` / `--to-date`로 통일.

### 5.2 데이터 구조 (Pydantic v2 기준, dataclass 미사용)

```python
# mixpanel_cli/models.py

from pydantic import BaseModel
from typing import Any, Optional, Literal

class Profile(BaseModel):
    name: str
    service_account_username: str
    project_id: str
    region: Literal["us", "eu", "in"] = "us"
    # secret은 OS keychain에 별도 저장

class CLIResponse(BaseModel):
    status: Literal["ok", "error"]
    data: Optional[Any] = None
    meta: Optional[dict] = None
    code: Optional[str] = None      # 에러 시
    message: Optional[str] = None   # 에러 시

class AskResponse(CLIResponse):
    summary: Optional[str] = None
    query_used: Optional[dict] = None
```

### 5.3 API 엔드포인트 매핑

**공식 API (안정적)**

| CLI 명령 | Mixpanel API | 메서드 |
|---------|-------------|--------|
| `project list/info` | `/api/2.0/projects` | GET |
| `analytics insight` | `/api/2.0/insights` | GET |
| `analytics funnel` | `/api/2.0/funnels` | GET |
| `analytics retention` | `/api/2.0/retention` | GET |
| `analytics flow` | `/api/2.0/flows` | GET |
| `events list` | `/api/2.0/events/names` | GET |
| `events properties` | `/api/2.0/events/properties` | GET |
| `export events` | `data.mixpanel.com/api/2.0/export` | GET (스트리밍) |

**비공식 API (Phase 1b, 변경 가능)**

| CLI 명령 | Mixpanel API (비공식) | 비고 |
|---------|-------------|--------|
| `dashboard list` | `/api/app/projects/{id}/bookmarks` | `/api/app/` = 내부 API |
| `dashboard create/update` | `/api/app/projects/{id}/bookmarks` | POST/PATCH |
| `lexicon list` | `/api/app/projects/{id}/schemas/events` | 내부 API |
| `lexicon edit-event` | `/api/app/projects/{id}/schemas/events/{name}` | PATCH |

> 비공식 API는 응답 스키마 검증 후 `API_CHANGED` 에러로 graceful 처리 필수.

### 5.4 리전별 베이스 URL

```python
# mixpanel_cli/constants.py

REGION_URLS: dict[str, dict[str, str]] = {
    "us": {
        "api":       "https://mixpanel.com",
        "data":      "https://data.mixpanel.com",
        "ingestion": "https://api.mixpanel.com",
    },
    "eu": {
        "api":       "https://eu.mixpanel.com",
        "data":      "https://eu.data.mixpanel.com",
        "ingestion": "https://api-eu.mixpanel.com",
    },
    "in": {
        "api":       "https://in.mixpanel.com",
        "data":      "https://in.data.mixpanel.com",
        "ingestion": "https://api-in.mixpanel.com",
    },
}

DEFAULT_TIMEOUT = 30  # 초
DEFAULT_EXPORT_CHUNK_DAYS = 30  # Raw Export 최대 날짜 범위
EVENTS_CACHE_TTL = 3600  # 초 (ask 명령용 이벤트 목록 캐시)
```

### 5.5 인증 로직

```
우선순위 (높은 순):
  1. CLI 플래그: --username, --secret
  2. 환경변수: MIXPANEL_USERNAME, MIXPANEL_SECRET, MIXPANEL_PROJECT_ID
     → CI/Docker/에이전트 환경에서 권장
  3. 프로파일: ~/.mixpanel/profiles.json (username/project_id) + OS keychain (secret)

keyring 사용 불가 환경 처리:
  - keyring backend 없음 → RuntimeError 발생
  - 처리: 환경변수 사용 안내 후 AuthError 발생
  - .secrets 파일 fallback 없음 (보안 원칙 위반)
  - 에러 메시지: "keyring unavailable. Set MIXPANEL_SECRET env var instead."

인증 헤더:
  Authorization: Basic base64("{username}:{secret}")

에러 처리:
  - 401: AUTH_ERROR
  - 403: PERMISSION_ERROR
  - 429: RATE_LIMIT → 지수 백오프 재시도 (최대 3회, 1s/2s/4s)
```

### 5.6 `ask` 명령 AI 파이프라인 (최적화)

```
사용자 자연어 입력
    ↓
[Step 1] 이벤트 목록 캐시 확인
  - ~/.mixpanel/cache/events_{project_id}.json 존재 + TTL 1시간 이내: 캐시 사용
  - 캐시 없거나 만료: /api/2.0/events/names 호출 후 캐시 저장
  (--refresh-cache 플래그: 강제 캐시 무효화)
    ↓
[Step 2] Claude API 호출 1회 (claude-haiku-4-5)
  System: "Mixpanel 쿼리 전문가. 자연어를 Mixpanel API 파라미터 JSON으로 변환하고,
           결과 요약을 위한 템플릿도 함께 생성하라."
  User: "{자연어}\n\n오늘 날짜: {today}\n사용 가능한 이벤트: {event_list}"
  출력: {
    "query": {"api": "insights", "params": {...}},
    "summary_template": "총 {total}건의 {event}이 발생했으며..."
  }
    ↓
[Step 3] --dry-run이면 query 파라미터만 출력 후 종료
    ↓
[Step 4] Mixpanel API 호출
    ↓
[Step 5] 요약 템플릿에 실제 값 채움 (Claude 2차 호출 없음)
    ↓
[Step 6] AskResponse 반환
```

**Claude API 인증:**
```bash
# 환경변수 (필수)
export ANTHROPIC_API_KEY="sk-ant-..."
# 또는 config에 추가
mixpanel config set --key anthropic_api_key --value "sk-ant-..."
```

### 5.7 예외 처리

```python
# mixpanel_cli/exceptions.py

class MixpanelCLIError(Exception):
    code: str
    message: str

class AuthError(MixpanelCLIError):      code = "AUTH_ERROR"
class PermissionError(MixpanelCLIError): code = "PERMISSION_ERROR"
class NotFoundError(MixpanelCLIError):  code = "NOT_FOUND"
class RateLimitError(MixpanelCLIError): code = "RATE_LIMIT"
class QueryError(MixpanelCLIError):     code = "QUERY_ERROR"
class AIParseError(MixpanelCLIError):   code = "AI_PARSE_ERROR"
class AINotInstalledError(MixpanelCLIError): code = "AI_NOT_INSTALLED"
class ProfileNotFoundError(MixpanelCLIError): code = "PROFILE_NOT_FOUND"
class APIChangedError(MixpanelCLIError): code = "API_CHANGED"  # 비공식 API 스키마 변경
```

| 에러 코드 | 발생 조건 | 처리 방법 |
|----------|---------|---------|
| `AUTH_ERROR` | 인증 실패 (401) | stderr에 재설정 안내 |
| `PERMISSION_ERROR` | 권한 없음 (403) | 프로파일 확인 안내 |
| `NOT_FOUND` | 리소스 없음 (404) | ID 확인 안내 |
| `RATE_LIMIT` | 요청 한도 초과 (429) | 지수 백오프 3회 자동 재시도 |
| `QUERY_ERROR` | 잘못된 쿼리 (400) | 파라미터 검토 안내 |
| `AI_PARSE_ERROR` | ask 명령 파싱 실패 | 직접 명령 사용 유도 |
| `AI_NOT_INSTALLED` | anthropic 미설치 | `pip install mixpanel-cli[ai]` 안내 |
| `PROFILE_NOT_FOUND` | 프로파일 없음 | `config init` 실행 안내 |
| `API_CHANGED` | 비공식 API 스키마 변경 | 이슈 리포트 안내 |

---

## 6. CLI-Anything 패턴 적용

### 6.1 JSON 출력 원칙
- 모든 명령의 stdout: 유효한 JSON (또는 JSONL for export)
- 상태 메시지, 경고, 진행률: 반드시 stderr
- `--quiet` 플래그: `data` 필드 값을 `json.dumps(data)` 출력 (항상 유효한 JSON 유지)
- `--pretty` 플래그: `json.dumps(..., indent=2, ensure_ascii=False)` (기본: compact)
- `--format [json|csv|table]`: analytics 명령의 출력 형식 (export의 `--file`과 별개)

### 6.2 전역 플래그

```bash
mixpanel [GLOBAL_OPTIONS] COMMAND [ARGS]

Global Options:
  --profile TEXT          사용할 프로파일명 (기본: default)
  --project-id TEXT       프로젝트 ID 오버라이드
  --region [us|eu|in]     리전 오버라이드
  --pretty                JSON pretty print
  --quiet                 data 값만 출력
  --no-color              컬러 출력 비활성화
  --debug                 요청/응답 디버그 출력 (secret 마스킹)
  --timeout INTEGER       HTTP 타임아웃 초 (기본: 30)
  -v, --version           버전 출력
  --help                  도움말
```

### 6.3 REPL 모드

```python
REPL_COMMANDS = {
    "use project <id>":   "활성 프로젝트 전환",
    "use profile <name>": "활성 프로파일 전환",
    "history":            "이전 쿼리 목록 출력",
    "clear":              "화면 클리어",
    "exit / quit / Ctrl+D": "종료",
}
# prompt-toolkit 기반 자동완성
# 쿼리 이력 ~/.mixpanel/history 저장
```

### 6.4 SKILL.md (Claude Code 에이전트용)

```markdown
# mixpanel-cli SKILL

## 설치
pip install mixpanel-cli          # Phase 1 (기본 CLI)
pip install mixpanel-cli[ai]      # Phase 2 (자연어 쿼리 포함)

## 인증 설정
# 대화형
mixpanel config init

# CI/에이전트 환경 (환경변수)
export MIXPANEL_USERNAME="..."
export MIXPANEL_SECRET="..."
export MIXPANEL_PROJECT_ID="..."

## 주요 명령 패턴

### 이벤트 분석 (에이전트 권장)
mixpanel analytics insight --event "Sign Up" \
  --from-date 2026-03-01 --to-date 2026-03-26 --quiet | jq .

### 자연어 쿼리 (AI 기능, [ai] 필요)
mixpanel ask "지난 30일 결제 완료 이벤트 일별 추이" --dry-run  # 먼저 검증
mixpanel ask "지난 30일 결제 완료 이벤트 일별 추이"            # 실행

### 대시보드 목록
mixpanel dashboard list --quiet

### 이벤트 목록 확인
mixpanel events list --quiet

## 에이전트 팁
- 항상 --quiet 플래그로 순수 JSON 데이터만 받기
- ask --dry-run으로 생성된 쿼리 검증 후 실행
- MIXPANEL_PROJECT_ID 환경변수로 프로젝트 고정
- 에러 시 .code 필드로 원인 파악
```

---

## 7. Tech Stack

### 핵심 의존성 (Optional extras 분리)

```toml
[project]
name = "mixpanel-cli"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
  "click>=8.1",           # CLI 프레임워크
  "httpx>=0.27",          # HTTP 클라이언트 (sync, export용 streaming)
  "keyring>=25.0",        # OS 키체인 인증 저장
  "rich>=13.0",           # 컬러 출력, 프로그레스 (stderr용)
  "pydantic>=2.0",        # 데이터 검증 및 직렬화
]

[project.optional-dependencies]
ai    = ["anthropic>=0.25"]         # ask 명령
shell = ["prompt-toolkit>=3.0"]     # REPL 모드
all   = ["mixpanel-cli[ai,shell]"]

[project.scripts]
mixpanel = "mixpanel_cli.main:cli"
```

### 프로젝트 구조 (최종)

```
mixpanel-cli/
├── mixpanel_cli/
│   ├── __init__.py
│   ├── main.py                    # Click CLI 진입점, 전역 플래그
│   ├── models.py                  # Pydantic 모델 (CLIResponse, Profile, AskResponse)
│   ├── exceptions.py              # 커스텀 예외 계층
│   ├── constants.py               # REGION_URLS, TTL, 기본값
│   ├── types.py                   # Click 커스텀 타입 (DateType, RegionType)
│   ├── commands/
│   │   ├── __init__.py            # Click group 등록
│   │   ├── config.py              # config 명령 그룹
│   │   ├── project.py             # project 명령 그룹
│   │   ├── analytics.py           # analytics 명령 그룹 (공식 API)
│   │   ├── events.py              # events 명령 그룹 (공식 API)
│   │   ├── dashboard.py           # dashboard 명령 그룹 (비공식 API, Phase 1b)
│   │   ├── export.py              # export 명령 그룹 (공식 API)
│   │   ├── lexicon.py             # lexicon 명령 그룹 (비공식 API, Phase 1b)
│   │   ├── ask.py                 # ask 명령 (AI, Phase 2)
│   │   ├── watch.py               # watch 명령 (Phase 2)
│   │   └── shell.py               # REPL 모드 (Phase 2)
│   ├── client/
│   │   ├── __init__.py
│   │   ├── base.py                # 공통 HTTP (retry, rate-limit, auth header, timeout)
│   │   ├── mixpanel.py            # Mixpanel API 클라이언트 (base 상속)
│   │   └── claude.py              # Claude API 클라이언트 (lazy import)
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── profile.py             # 프로파일 CRUD
│   │   └── keychain.py            # keyring wrapper + headless 에러 처리
│   └── output/
│       ├── __init__.py
│       └── formatter.py           # JSON/CSV/table 출력 포매터
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # 공통 픽스처 (respx mock, anthropic mock)
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_analytics.py
│   │   ├── test_events.py
│   │   ├── test_export.py
│   │   ├── test_dashboard.py
│   │   ├── test_ask.py
│   │   └── test_formatter.py
│   ├── e2e/
│   │   ├── test_insight_e2e.py
│   │   ├── test_funnel_e2e.py
│   │   └── test_ask_e2e.py
│   └── fixtures/
│       └── ask_golden_set.json    # ask 정확도 평가용 golden set (20-30개)
├── SKILL.md                       # Claude Code 에이전트용 스킬 정의
├── TEST.md                        # 테스트 전략 문서
├── pyproject.toml
└── README.md
```

### 인증 저장 방식
- **프로파일 메타:** `~/.mixpanel/profiles.json` (평문: username, project_id, region만)
- **Secret:** OS keychain (`keyring`) — macOS Keychain / Linux Secret Service / Windows Credential Manager
- **Secret 파일 저장 금지:** `.secrets` fallback 없음. keyring 불가 환경은 반드시 환경변수 사용
- **CI 환경:** `MIXPANEL_USERNAME`, `MIXPANEL_SECRET`, `MIXPANEL_PROJECT_ID` 환경변수

---

## 8. 구현 우선순위

### Phase 1a — 공식 API Foundation (Week 1)

**완료 기준:** `mixpanel analytics insight`가 올바른 JSON을 반환하고 SKILL.md v1이 존재함

- [ ] 프로젝트 세팅 (pyproject.toml, uv/pip 설치 확인)
- [ ] `models.py`, `exceptions.py`, `constants.py`, `types.py` 공통 레이어
- [ ] `client/base.py` — HTTP 기반 (retry, rate-limit, timeout, auth header)
- [ ] `client/mixpanel.py` — 공식 API 엔드포인트 구현
- [ ] `auth/profile.py` + `auth/keychain.py` — 프로파일 CRUD + keyring
- [ ] `output/formatter.py` — JSON/CSV/table 출력, `--quiet`, `--pretty`
- [ ] `commands/config.py` — `init/list/show/set/delete`
- [ ] `commands/project.py` — `info/list`
- [ ] `commands/analytics.py` — `insight/funnel/retention/flow`
- [ ] `commands/events.py` — `list/get/properties` (페이지네이션 포함)
- [ ] `commands/export.py` — `events` (스트리밍 JSONL, 30일 자동 청킹)
- [ ] 단위 테스트 — `respx`로 httpx mock (커버리지 90% 이상)
- [ ] `SKILL.md` v1 작성

### Phase 1b — 비공식 API 검증 및 추가 (Week 2)

**완료 기준:** `mixpanel dashboard list`가 올바른 JSON을 반환하거나 `API_CHANGED` 에러를 구조화하여 반환함

- [ ] 비공식 API 엔드포인트 실제 동작 검증 (수동 테스트)
- [ ] 응답 스키마 pydantic 모델 정의 + `API_CHANGED` 에러 처리 추가
- [ ] `commands/dashboard.py` — `list/get/create/update/duplicate/delete` (첫 사용 경고 포함)
- [ ] `commands/lexicon.py` — `list/edit-event/edit-property`
- [ ] 단위 테스트 — 정상 응답 + 스키마 변경 응답 모두 mock
- [ ] `SKILL.md` v1.1 업데이트 (dashboard/lexicon 추가)

> 비공식 API가 동작하지 않으면 Phase 2로 이동하고 해당 명령은 `--experimental` 플래그로 숨김 처리

### Phase 2 — AI Intelligence Layer (Week 3-4)

**완료 기준:** `mixpanel ask`가 golden set 20문항 중 16개 이상 정확한 파라미터를 생성함

- [ ] `client/claude.py` — Claude API lazy import, ANTHROPIC_API_KEY 검증
- [ ] 이벤트 목록 TTL 캐시 (`~/.mixpanel/cache/`)
- [ ] `commands/ask.py` — 1회 Claude 호출 파이프라인 구현
- [ ] `ask --dry-run`, `--explain`, `--no-summary`, `--refresh-cache`
- [ ] `tests/fixtures/ask_golden_set.json` 작성 (20-30개 쿼리-정답 쌍)
- [ ] ask 정확도 테스트 (`pytest -m golden`)
- [ ] `commands/shell.py` — prompt-toolkit REPL (lazy import)
- [ ] `commands/watch.py` — 폴링 + 웹훅 (foreground blocking)
- [ ] E2E 테스트 (실제 API, `.env` 파일 필요)
- [ ] PyPI 배포 준비 (`pip install mixpanel-cli`)
- [ ] `SKILL.md` v2 업데이트 (ask, shell 추가)

### Phase 3 — 고급 기능 (Week 5+)

- [ ] `mixpanel report generate --template weekly` — 자동 보고서
- [ ] 여러 프로젝트 비교 분석
- [ ] `--log-file` 옵션으로 디버그 로그 영속화
- [ ] Claude Code 네이티브 MCP 도구로 등록 (옵션)

---

## 9. 테스트 전략

### 모킹 전략
```python
# tests/conftest.py
import respx           # httpx mock
import pytest
from anthropic import Anthropic

@pytest.fixture
def mock_mixpanel():
    with respx.mock(base_url="https://mixpanel.com") as respx_mock:
        yield respx_mock

@pytest.fixture
def mock_anthropic(mocker):
    # anthropic SDK mock (pytest-mock 활용)
    return mocker.patch("mixpanel_cli.client.claude.Anthropic")

@pytest.fixture(autouse=True)
def mock_keyring(mocker):
    mocker.patch("keyring.get_password", return_value="test-secret")
    mocker.patch("keyring.set_password")
```

### ask 정확도 평가 (golden set)
```json
// tests/fixtures/ask_golden_set.json
[
  {
    "query": "지난 7일 Sign Up 이벤트 일별 카운트",
    "expected_params": {
      "api": "insights",
      "event": "Sign Up",
      "unit": "day",
      "from_date_offset": -7
    }
  },
  // ... 20-30개
]
```
정확도: expected_params의 핵심 필드(api, event, unit) 모두 일치 시 정답으로 판정.

### 커버리지 목표
- 단위 테스트: 90% 이상
- E2E: insight, funnel, retention, export, ask 100%
- 에러 케이스: AUTH_ERROR, RATE_LIMIT, QUERY_ERROR, API_CHANGED 모두 커버

```bash
# 단위 테스트 (mock)
pytest tests/unit/ -v --cov=mixpanel_cli --cov-report=term-missing

# ask 정확도 테스트
pytest tests/unit/test_ask.py -m golden -v

# E2E (실제 API)
MIXPANEL_TEST_PROJECT_ID=xxx pytest tests/e2e/ -v
```

---

## 10. 성공 지표

| 지표 | 목표 | 측정 방법 |
|-----|-----|---------|
| `ask` 쿼리 정확도 | 80% (golden set 20문항 중 16개) | `pytest -m golden` CI 실행 |
| CLI 응답 시간 | 단순 조회 < 2초, ask < 5초 | pytest-benchmark 측정 |
| 에이전트 사용 성공률 | SKILL.md 기반 95% 이상 | E2E 시나리오 테스트 |
| 설치 ~ 첫 쿼리 | 5분 이내 | 타이밍 스크립트 (`install_and_query.sh`) |

---

## 11. 보안 고려사항

- **Secret 저장 원칙:** Service Account Secret은 OS keychain에만 저장. 파일 평문 저장 절대 금지
- **keyring 불가 환경:** `.secrets` 파일 fallback 없음. 환경변수 `MIXPANEL_SECRET` 사용 필수. 에러 메시지로 안내
- **`--debug` 모드:** secret 값은 항상 `***` 마스킹
- **Claude API 키 (ANTHROPIC_API_KEY):** 환경변수 또는 `config set --key anthropic_api_key` (keychain 저장)
- **ask 명령:** Mixpanel 이벤트 이름 목록이 Claude API로 전송됨 — 이벤트명에 PII가 포함된 경우 주의
- **HIPAA 프로젝트:** ask, watch 명령 미사용 권장
- **비공식 API:** dashboard, lexicon 명령 사용 시 내부 API 호출 경고 출력

---

**이 PRD는 Claude Code 에이전트에게 전달하여 즉시 구현을 시작할 수 있습니다. (v1.1)**
