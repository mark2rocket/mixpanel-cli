# mixpanel-cli TODO

**기준 버전:** PRD v1.1
**최종 업데이트:** 2026-03-26

---

## Phase 1a — 공식 API Foundation (Week 1)

> 완료 기준: `mixpanel analytics insight`가 올바른 JSON 반환 + SKILL.md v1 존재

### STEP 1: 프로젝트 초기화
- [ ] `pyproject.toml` 작성 (의존성 분리: base / `[ai]` / `[shell]` / `[all]`)
- [ ] `uv init` 또는 `pip install -e ".[all]"` 개발 환경 세팅
- [ ] `.gitignore` 작성 (`.env`, `~/.mixpanel/`, `__pycache__`, `.pytest_cache`)
- [ ] `tests/conftest.py` 공통 픽스처 작성 (`respx` mock, `keyring` mock)

### STEP 2: 공통 인프라 레이어
- [ ] `mixpanel_cli/constants.py` — `REGION_URLS`, `DEFAULT_TIMEOUT`, `DEFAULT_EXPORT_CHUNK_DAYS`, `EVENTS_CACHE_TTL`
- [ ] `mixpanel_cli/exceptions.py` — `MixpanelCLIError` 계층 (8개 에러 코드)
- [ ] `mixpanel_cli/models.py` — `Profile`, `CLIResponse`, `AskResponse` (Pydantic v2)
- [ ] `mixpanel_cli/types.py` — Click 커스텀 타입 (`DateType` YYYY-MM-DD 검증, `RegionType`)
- [ ] `mixpanel_cli/output/formatter.py` — JSON/CSV/table 출력 (`--quiet`, `--pretty`, `--format`)

### STEP 3: HTTP 클라이언트
- [ ] `mixpanel_cli/client/base.py`
  - [ ] `Authorization: Basic base64(username:secret)` 헤더 주입
  - [ ] 지수 백오프 재시도 (429: 1s/2s/4s, 최대 3회)
  - [ ] HTTP 타임아웃 (기본 30초, `--timeout` 오버라이드)
  - [ ] `--debug` 모드: 요청/응답 stderr 출력 (secret `***` 마스킹)
- [ ] `mixpanel_cli/client/mixpanel.py`
  - [ ] 리전별 베이스 URL 라우팅 (`REGION_URLS` 참조)
  - [ ] 공식 API 메서드: `get_projects`, `get_insight`, `get_funnel`, `get_retention`, `get_flow`
  - [ ] `get_event_names` (이벤트 목록, ask 캐싱용)
  - [ ] `get_event_properties`
  - [ ] `export_events` (스트리밍 JSONL, 30일 자동 청킹)

### STEP 4: 인증 레이어
- [ ] `mixpanel_cli/auth/keychain.py`
  - [ ] `set_secret(profile_name, secret)` — keyring 저장
  - [ ] `get_secret(profile_name)` — keyring 조회
  - [ ] keyring `RuntimeError` 시: `"keyring unavailable. Set MIXPANEL_SECRET env var instead."` 에러
- [ ] `mixpanel_cli/auth/profile.py`
  - [ ] `~/.mixpanel/profiles.json` CRUD (secret 미포함)
  - [ ] 인증 우선순위 해결: CLI 플래그 → 환경변수 → 프로파일+keychain

### STEP 5: CLI 진입점 및 전역 플래그
- [ ] `mixpanel_cli/main.py`
  - [ ] Click `@group()` 설정
  - [ ] 전역 플래그: `--profile`, `--project-id`, `--region`, `--pretty`, `--quiet`, `--no-color`, `--debug`, `--timeout`
  - [ ] Click `Context` 객체로 인증 정보 하위 명령에 전달 (`pass_context`)
- [ ] `mixpanel_cli/commands/__init__.py` — 명령 그룹 등록

### STEP 6: config 명령
- [ ] `mixpanel_cli/commands/config.py`
  - [ ] `config init` — 프롬프트 입력, keychain 저장, 연결 테스트 (`GET /api/2.0/projects`)
  - [ ] `config list` — 프로파일 목록 (secret 미포함)
  - [ ] `config show --profile <name>`
  - [ ] `config set --key <field> --value <value>` — 단일 필드 수정
  - [ ] `config delete --profile <name>`
- [ ] 단위 테스트: `tests/unit/test_config.py`

### STEP 7: project 명령
- [ ] `mixpanel_cli/commands/project.py`
  - [ ] `project info` → `GET /api/2.0/projects`
  - [ ] `project list`
- [ ] 단위 테스트: `tests/unit/test_project.py`

### STEP 8: analytics 명령
- [ ] `mixpanel_cli/commands/analytics.py`
  - [ ] `analytics insight --event --from-date --to-date [--unit] [--format]`
  - [ ] `analytics funnel --id --from-date --to-date`
  - [ ] `analytics retention --event --from-date --to-date [--unit]`
  - [ ] `analytics flow --event --from-date --to-date`
  - [ ] `--from-date` / `--to-date` 예약어 remapping (`from_date`, `to_date`)
- [ ] 단위 테스트: `tests/unit/test_analytics.py` (respx mock)

### STEP 9: events 명령
- [ ] `mixpanel_cli/commands/events.py`
  - [ ] `events list [--limit] [--search] [--page]` — 페이지네이션 포함
  - [ ] `events get --name`
  - [ ] `events properties --event`
- [ ] 단위 테스트: `tests/unit/test_events.py`

### STEP 10: export 명령
- [ ] `mixpanel_cli/commands/export.py`
  - [ ] `export events --from-date --to-date [--event-name] [--file] [--timeout]`
  - [ ] 30일 초과 자동 청킹 (30일 단위 분할 요청 후 JSONL 병합)
  - [ ] 스트리밍 저장 (대용량 데이터)
  - [ ] 진행률 stderr 출력
- [ ] 단위 테스트: `tests/unit/test_export.py`

### STEP 11: Phase 1a 검증
- [ ] `pytest tests/unit/ --cov=mixpanel_cli --cov-report=term-missing` → 90% 이상
- [ ] `mixpanel --help` 출력 정상 확인
- [ ] `SKILL.md` v1 작성 (config, project, analytics, events, export 패턴 문서화)
- [ ] `README.md` Phase 1a 범위 초안 작성

---

## Phase 1b — 비공식 API 검증 및 추가 (Week 2)

> 완료 기준: `mixpanel dashboard list`가 JSON 반환 또는 `API_CHANGED` 에러 구조화 반환

### STEP 12: 비공식 API 검증 (수동)
- [ ] Mixpanel 계정으로 `GET /api/app/projects/{id}/bookmarks` 실제 호출 테스트
- [ ] `GET /api/app/projects/{id}/schemas/events` 실제 호출 테스트
- [ ] 응답 스키마 문서화 → `tests/fixtures/dashboard_response.json`, `lexicon_response.json`
- [ ] 동작 안 하면: Phase 2로 이동, `--experimental` 플래그로 숨김 처리

### STEP 13: dashboard 명령 (비공식 API)
- [ ] `mixpanel_cli/commands/dashboard.py`
  - [ ] 응답 스키마 Pydantic 모델 정의
  - [ ] `API_CHANGED` 에러: 응답 스키마 불일치 시 구조화된 에러 반환
  - [ ] 첫 사용 시 stderr 경고: `[WARNING] dashboard commands use an undocumented API`
  - [ ] `dashboard list / get / create / update / duplicate / delete`
- [ ] 단위 테스트: 정상 응답 + 스키마 변경 케이스 모두 mock

### STEP 14: lexicon 명령 (비공식 API)
- [ ] `mixpanel_cli/commands/lexicon.py`
  - [ ] 동일한 `API_CHANGED` 처리 패턴 적용
  - [ ] `lexicon list / edit-event / edit-property`
- [ ] 단위 테스트

### STEP 15: Phase 1b 검증
- [ ] `pytest tests/unit/ --cov=mixpanel_cli` → 90% 유지
- [ ] `SKILL.md` v1.1 업데이트 (dashboard, lexicon 추가)

---

## Phase 2 — AI Intelligence Layer (Week 3-4)

> 완료 기준: `mixpanel ask`가 golden set 20문항 중 16개 이상 정확한 파라미터 생성

### STEP 16: Claude API 클라이언트
- [ ] `mixpanel_cli/client/claude.py`
  - [ ] `anthropic` lazy import (미설치 시 `AI_NOT_INSTALLED` 에러)
  - [ ] `ANTHROPIC_API_KEY` 검증 (환경변수 또는 keychain)
  - [ ] 1회 호출로 쿼리 파라미터 + 요약 템플릿 동시 생성
  - [ ] Claude API 429 처리 (rate limit)

### STEP 17: 이벤트 캐시
- [ ] `~/.mixpanel/cache/events_{project_id}.json` TTL 1시간 캐시
- [ ] `--refresh-cache` 플래그로 강제 무효화
- [ ] 캐시 만료 시 자동 갱신

### STEP 18: ask 명령
- [ ] `mixpanel_cli/commands/ask.py`
  - [ ] 캐시 확인 → Claude 1회 호출 → API 실행 → 요약 채우기 파이프라인
  - [ ] `--dry-run`: 파라미터만 출력 후 종료
  - [ ] `--explain`: 쿼리 구성 이유 포함 출력
  - [ ] `--no-summary`: 자연어 요약 없이 raw 데이터만 반환
  - [ ] `--refresh-cache`: 이벤트 목록 강제 갱신
- [ ] `tests/fixtures/ask_golden_set.json` 작성 (20-30개 쿼리-정답 쌍)
- [ ] 단위 테스트: `tests/unit/test_ask.py` (anthropic mock + respx mock)
- [ ] golden set 정확도 테스트: `pytest tests/unit/test_ask.py -m golden`

### STEP 19: shell REPL 모드
- [ ] `mixpanel_cli/commands/shell.py`
  - [ ] `prompt-toolkit` lazy import (미설치 시 `pip install mixpanel-cli[shell]` 안내)
  - [ ] Click 명령 파싱 레이어 (REPL 입력 → Click invoke)
  - [ ] `use project <id>`, `use profile <name>`, `history`, `clear`, `exit`
  - [ ] `~/.mixpanel/history` 히스토리 저장
  - [ ] 자동완성 (명령어 목록)

### STEP 20: watch 명령
- [ ] `mixpanel_cli/commands/watch.py`
  - [ ] foreground blocking 폴링 루프
  - [ ] `--interval <minutes>` (기본: 60)
  - [ ] `--threshold-drop <pct>`, `--threshold-rise <pct>`
  - [ ] `--webhook <url>` JSON POST 알림
  - [ ] Ctrl+C graceful 종료

### STEP 21: E2E 테스트
- [ ] `tests/e2e/test_insight_e2e.py` (실제 Mixpanel API)
- [ ] `tests/e2e/test_funnel_e2e.py`
- [ ] `tests/e2e/test_ask_e2e.py` (실제 Claude API + Mixpanel API)
- [ ] `.env.example` 작성 (`MIXPANEL_USERNAME`, `MIXPANEL_SECRET`, `MIXPANEL_PROJECT_ID`, `ANTHROPIC_API_KEY`)

### STEP 22: Phase 2 검증 및 배포
- [ ] `pytest tests/unit/ tests/e2e/ --cov=mixpanel_cli`
- [ ] `ask` golden set 정확도 80% 이상 확인
- [ ] `SKILL.md` v2 업데이트 (ask, shell 추가)
- [ ] `pyproject.toml` 버전 `0.1.0` 확인
- [ ] `python -m build` 패키지 빌드 테스트
- [ ] PyPI 배포: `twine upload dist/*`

---

## Phase 3 — 고급 기능 (Week 5+)

- [ ] 쿼리 결과 로컬 캐싱 (`~/.mixpanel/cache/queries/`)
- [ ] `mixpanel report generate --template weekly` — 자동 보고서
- [ ] `--log-file <path>` 디버그 로그 영속화
- [ ] 여러 프로젝트 비교 분석
- [ ] Claude Code 네이티브 MCP 도구 등록 (옵션)

---

## 핵심 결정 사항 (ADR)

| 결정 | 드라이버 | 대안 검토 | 이유 |
|-----|---------|---------|-----|
| Optional extras `[ai]`, `[shell]` | Phase 1 경량 설치 | 전체 통합 설치 | Phase 1 사용자에게 불필요한 anthropic 의존성 제거 |
| keyring fallback 없음 | 보안 원칙 (파일 평문 금지) | `.secrets` 파일 | CI는 환경변수로 충분; fallback이 공격 표면 확대 |
| Phase 1a/1b 분리 | 비공식 API 리스크 | 한 번에 구현 | 공식 API 먼저 안정화 후 비공식 API 검증 |
| Claude 1회 호출 | 레이턴시 < 5초 목표 | 2회 호출 | 파라미터 생성 + 요약 템플릿을 1회에 처리 |
| `--from-date` (not `--from`) | Python 예약어 충돌 | `--start` | CLI 의미 명확성 유지하면서 충돌 회피 |
| Pydantic v2 (dataclass 아님) | 직렬화/검증 일관성 | `@dataclass` | JSON 출력 표준화에 Pydantic이 더 유리 |
