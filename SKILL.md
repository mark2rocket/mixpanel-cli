# mixpanel-cli SKILL

Agent-native Mixpanel CLI. JSON stdout, stderr 상태분리, 파이프라인 친화적.

## 설치

```bash
# Phase 1 (기본 CLI — config, analytics, events, export)
pip install mixpanel-cli

# Phase 2 포함 (AI 자연어 쿼리)
pip install mixpanel-cli[ai]

# 전체
pip install mixpanel-cli[all]
```

## 인증 설정

### OAuth 로그인 (권장 — 전체 권한)
```bash
# 브라우저 OAuth 로그인 (대시보드 수정 등 전체 권한)
mixpanel auth login --project-id 123456
mixpanel auth status   # 상태 확인
mixpanel auth logout   # 로그아웃
```

### Service Account (CI/에이전트 권장)
```bash
export MIXPANEL_USERNAME="svc-account@123456.mixpanel.com"
export MIXPANEL_SECRET="your-service-account-secret"
export MIXPANEL_PROJECT_ID="123456"
```

### 대화형 프로파일 (로컬 개발)
```bash
mixpanel config init
# → username, secret, project_id, region 순서로 입력
```

### 인증 우선순위
`CLI 플래그` > `환경변수` > `OAuth 토큰` > `Service Account 프로파일`

## 에이전트 핵심 패턴

### 이벤트 분석 (JSON 직접 파이프)
```bash
mixpanel analytics insight \
  --event "Sign Up" \
  --from-date 2026-03-01 \
  --to-date 2026-03-26 \
  --quiet | jq '.values["Sign Up"]'
```

### 펀넬 분석
```bash
mixpanel analytics funnel \
  --id 12345 \
  --from-date 2026-03-01 \
  --to-date 2026-03-26 \
  --quiet
```

### Retention 분석
```bash
mixpanel analytics retention \
  --event "Sign Up" \
  --from-date 2026-03-01 \
  --to-date 2026-03-26 \
  --unit week \
  --quiet
```

### 이벤트 목록 확인
```bash
mixpanel events list --quiet | jq '.[]'
mixpanel events list --search "Purchase" --quiet
mixpanel events properties --event "Purchase" --quiet
```

### Raw 데이터 Export
```bash
# 파일로 저장
mixpanel export events \
  --from-date 2026-03-01 \
  --to-date 2026-03-26 \
  --event-name "Purchase" \
  --file events.jsonl

# stdout 스트리밍 (30일 자동 청킹)
mixpanel export events \
  --from-date 2026-01-01 \
  --to-date 2026-03-31 \
  --quiet > all_events.jsonl
```

### 프로파일 관리
```bash
mixpanel config list --quiet
mixpanel config show --profile prod --quiet
mixpanel config set --key region --value eu
mixpanel --profile staging analytics insight --event "Login" --from-date 2026-03-01 --to-date 2026-03-26
```

### 멀티 리전
```bash
mixpanel --region eu analytics insight --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-26
```

## 전역 플래그

| 플래그 | 설명 |
|-------|------|
| `--profile <name>` | 사용할 프로파일 (기본: default) |
| `--project-id <id>` | 프로젝트 ID 오버라이드 |
| `--region us\|eu\|in` | 리전 오버라이드 |
| `--quiet` | data 값만 JSON 출력 (파이프 친화) |
| `--pretty` | JSON pretty print |
| `--debug` | HTTP 요청/응답 디버그 출력 (stderr) |
| `--timeout <seconds>` | HTTP 타임아웃 (기본 30초) |

## 출력 형식

모든 성공 응답:
```json
{"status": "ok", "data": {...}, "meta": {"query_time_ms": 120}}
```

모든 에러 응답 (stdout, 항상 유효한 JSON):
```json
{"status": "error", "code": "AUTH_ERROR", "message": "..."}
```

`--quiet` 플래그: `data` 값만 출력 (항상 유효한 JSON)

## Dashboard (비공식 API)

> **주의:** 비공식 API 사용 — Mixpanel 업데이트 시 동작이 변경될 수 있음. stderr에 경고 출력.

```bash
# 대시보드 목록
mixpanel dashboard list --quiet

# 특정 대시보드 조회
mixpanel dashboard get --id 123456 --quiet

# 새 대시보드 생성
mixpanel dashboard create --title "Weekly KPI"

# 대시보드 수정
mixpanel dashboard update --id 123456 --title "Monthly KPI"

# 대시보드 삭제
mixpanel dashboard delete --id 123456
```

API_CHANGED 에러 시 Mixpanel이 비공식 API를 변경한 것. 공식 지원 기능으로 대체 필요.

## Lexicon (비공식 API)

> **주의:** 비공식 API 사용 — 이벤트/프로퍼티 메타데이터 카탈로그.

```bash
# 이벤트 목록 + 설명 조회
mixpanel lexicon list --quiet | jq '.[] | {name, description, status}'

# 이벤트 메타데이터 수정
mixpanel lexicon edit-event \
  --event "Sign Up" \
  --description "신규 사용자 가입 완료 이벤트" \
  --status active

# 프로퍼티 설명 수정
mixpanel lexicon edit-property \
  --event "Sign Up" \
  --property "email" \
  --description "가입 시 사용한 이메일"
```

## 에러 코드 (전체)

| 코드 | 의미 | 해결 |
|-----|------|------|
| `AUTH_ERROR` | 인증 실패 | `mixpanel config init` 재실행 또는 환경변수 확인 |
| `PERMISSION_ERROR` | 권한 없음 | 프로젝트 접근 권한 확인 |
| `NOT_FOUND` | 리소스 없음 | ID 확인 |
| `RATE_LIMIT` | 요청 한도 초과 | 잠시 후 재시도 (자동 3회 재시도) |
| `QUERY_ERROR` | 잘못된 쿼리 | 파라미터 검토 |
| `PROFILE_NOT_FOUND` | 프로파일 없음 | `mixpanel config init` 실행 |
| `API_CHANGED` | 비공식 API 변경 감지 | 해당 명령 사용 중단, 공식 대안 확인 |

## AI 자연어 쿼리 (Phase 2)

> **설치:** `pip install mixpanel-cli[ai]` — `ANTHROPIC_API_KEY` 환경변수 필요

```bash
# 기본 자연어 쿼리
mixpanel ask query "지난 달 Sign Up 이벤트 몇 건이야?" --quiet

# 파라미터만 확인 (API 실행 안 함)
mixpanel ask query "이번 주 Purchase 추이" --dry-run

# 쿼리 구성 이유 포함
mixpanel ask query "Login 리텐션 보여줘" --explain

# 자연어 요약 없이 raw 데이터만
mixpanel ask query "Sign Up 플로우" --no-summary

# 이벤트 캐시 강제 갱신
mixpanel ask query "Sign Up 통계" --refresh-cache
```

## Shell REPL (Phase 2)

> **설치:** `pip install mixpanel-cli[shell]`

```bash
# REPL 시작
mixpanel shell start

# REPL 내부 명령
use project 123456    # 프로젝트 변경
use profile staging   # 프로파일 변경
history               # 히스토리 출력
clear                 # 화면 지우기
exit                  # 종료
```

## Watch 폴링 알림 (Phase 2)

```bash
# Sign Up 이벤트를 60분마다 모니터링, 20% 하락 시 알림
mixpanel watch start \
  --event "Sign Up" \
  --from-date 2026-03-01 \
  --to-date 2026-03-26 \
  --interval 60 \
  --threshold-drop 20 \
  --webhook https://hooks.example.com/alert

# Ctrl+C로 종료
```

## 에이전트 팁

1. **항상 `--quiet` 사용** — 순수 JSON 데이터만 받아 파싱
2. **환경변수로 인증** — CI/자동화 환경에서 `config init` 불필요
3. **`--debug` 로 문제 진단** — HTTP 요청/응답을 stderr로 출력
4. **export는 30일 자동 청킹** — 날짜 범위 제한 걱정 없음
5. **에러 시 `.code` 필드** — `"AUTH_ERROR"`, `"QUERY_ERROR"` 등으로 원인 파악
