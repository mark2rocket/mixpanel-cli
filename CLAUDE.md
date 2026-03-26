# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 개발 환경 설치
uv pip install --system -e ".[dev,ai,shell]"

# 전체 테스트
python3 -m pytest tests/ -v

# 단일 테스트 파일
python3 -m pytest tests/unit/test_analytics.py -v

# 단일 테스트 함수
python3 -m pytest tests/unit/test_ask.py::test_ask_query_dry_run -v

# Golden set 정확도 테스트만
python3 -m pytest tests/unit/test_ask.py -m golden -v

# 커버리지 포함
python3 -m pytest tests/ --cov=mixpanel_cli --cov-report=term-missing

# CLI 실행 (로컬 설치 후)
mixpanel --help
```

## 아키텍처

### 요청 흐름

```
CLI 입력 (Click)
  → main.py (AppContext 글로벌 플래그 설정)
  → commands/*.py (서브커맨드)
  → commands/_utils.py:make_client() (AuthContext + MixpanelClient 생성)
  → client/mixpanel.py (API 메서드)
  → client/base.py (HTTP, 재시도, 인증 헤더)
  → output/formatter.py (JSON 직렬화 + 출력)
```

### 출력 규칙

모든 명령은 `CLIResponse` (`models.py`) 를 통해 stdout에 JSON만 출력한다.

- 성공: `{"status": "ok", "data": {...}, "meta": {...}}`
- 실패: `{"status": "error", "code": "AUTH_ERROR", "message": "..."}`
- `--quiet`: `data` 값만 출력
- stderr: 디버그 로그, 비공식 API 경고(`[WARNING]`)

### 인증 우선순위

`AuthContext` (`auth/profile.py`) 가 해결 순서를 담당:
1. CLI 플래그 (`--project-id`, `--region`)
2. 환경변수 (`MIXPANEL_USERNAME`, `MIXPANEL_SECRET`, `MIXPANEL_PROJECT_ID`)
3. `~/.mixpanel/profiles.json` + keyring (`auth/keychain.py`)

### 새 명령 추가 패턴

```python
# 1. commands/new_cmd.py
@click.group("new-cmd")
def new_cmd_group(): ...

@new_cmd_group.command("action")
@click.pass_context
def action(ctx, ...):
    obj = ctx.obj
    client, auth = make_client(obj)  # _utils.py
    data = client.some_method(...)
    response = CLIResponse.ok(data=data)
    print_response(response, pretty=obj.pretty, quiet=obj.quiet)

# 2. main.py에 등록
cli.add_command(new_cmd.new_cmd_group, name="new-cmd")
```

### 비공식 API 명령 (dashboard, lexicon)

`client/mixpanel.py`에서 `/api/app/projects/{project_id}/...` 엔드포인트 사용.
응답 스키마가 예상과 다를 시 `APIChangedError` (코드: `API_CHANGED`) 발생.
커맨드 파일 상단에서 `click.echo(_WARN, file=sys.stderr)`로 경고 출력.

### Phase 2 선택적 의존성

- `ask` 명령: `anthropic` 패키지 필요 (`pip install mixpanel-cli[ai]`)
  - `client/claude.py`에서 **함수 레벨** lazy import — 모듈 레벨 import 금지
  - 단, `commands/ask.py`에서 `ClaudeClient`는 **모듈 레벨** import 필수 (mock 패치 가능하도록)
- `shell` 명령: `prompt_toolkit` 패키지 필요 (`pip install mixpanel-cli[shell]`)
  - `commands/shell.py`에서 lazy import

### 캐시

`cache.py`: 이벤트 목록을 `~/.mixpanel/cache/events_{project_id}.json`에 TTL 1시간 저장.

### 예외 계층

`exceptions.py`의 `MixpanelCLIError` 서브클래스가 각 에러 코드를 class attribute로 보유.
`HTTP_STATUS_TO_ERROR` dict로 HTTP 상태코드 → 예외 자동 매핑 (`client/base.py` 사용).

### 테스트 패턴

- HTTP mock: `respx` + `httpx` 사용 (`@respx.mock` 데코레이터)
- CLI 테스트: `click.testing.CliRunner`
- 인증: `env_auth` fixture (`monkeypatch`로 환경변수 주입)
- dashboard/lexicon 테스트: `_parse_json()` 헬퍼 사용 — stderr WARNING이 stdout에 섞일 수 있어 마지막 JSON 라인을 파싱
- golden set: `@pytest.mark.golden`으로 마킹, `tests/fixtures/ask_golden_set.json` 참조
