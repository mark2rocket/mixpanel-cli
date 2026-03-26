# /mixpanel-dashboard 스킬 — Mixpanel 대시보드 생성

> Mixpanel MCP를 통해 인사이트·펀넬·리텐션 리포트가 실제로 보이는 대시보드를 생성하는 Claude Code 전역 스킬.

---

## 설치

이 스킬은 Claude Code 전역 커맨드로 설치합니다.

```bash
# ~/.claude/commands/ 에 스킬 파일 저장
curl -o ~/.claude/commands/mixpanel-dashboard.md \
  https://raw.githubusercontent.com/kimsaeam/mixpanel-cli/master/docs/mixpanel-dashboard-skill.md
```

또는 이 저장소를 클론 후 직접 복사:

```bash
cp docs/mixpanel-dashboard-skill-source.md ~/.claude/commands/mixpanel-dashboard.md
```

---

## 사용법

Claude Code 대화에서 아래처럼 호출합니다:

```
/mixpanel-dashboard
```

또는 자연어로 트리거:
- "Mixpanel 대시보드 만들어줘"
- "대시보드에 리포트 추가해줘"
- "전환율 퍼널 대시보드 생성"
- "구독 리텐션 대시보드"

---

## 스킬이 하는 일

호출 즉시 필요한 정보를 질문합니다:

1. **대시보드 이름**
2. **Mixpanel 프로젝트 ID**
3. **목적** (마케팅/제품/리텐션 분석 등)
4. **포함할 리포트와 이벤트** (예: "구독 트렌드", "결제 퍼널: 상품조회→장바구니→결제")
5. **기간** (예: 최근 12주, 2026-01-01~2026-03-31)
6. **개선 제안사항 섹션 포함 여부**

정보를 받은 뒤 자동으로:
- Mixpanel MCP `Run-Query`로 각 리포트의 `query_id` 획득
- `Create-Dashboard`로 리포트가 포함된 대시보드 생성
- 완성된 대시보드 URL 반환

---

## 지원하는 리포트 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| **인사이트** | 트렌드·바·파이 차트 | 구독 트렌드, 이벤트별 발생 횟수 |
| **펀넬** | 단계별 전환율 | 랜딩→가입→결제 전환 퍼널 |
| **리텐션** | 재방문·재사용률 | 가입 후 핵심기능 재사용 리텐션 |

---

## 사전 조건

```bash
# OAuth 로그인 (user_details 스코프 포함)
mixpanel auth login --project-id YOUR_PROJECT_ID

# 현재 인증 상태 확인
mixpanel auth status
```

Mixpanel MCP가 Claude Desktop에 설정되어 있어야 합니다:

```json
// ~/.claude/claude_desktop_config.json
{
  "mcpServers": {
    "mixpanel": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.mixpanel.com/mcp"]
    }
  }
}
```

---

## MCP vs CLI — 대시보드 생성 비교

| | Mixpanel MCP (Claude Desktop) | mixpanel-cli + /mixpanel-dashboard |
|---|---|---|
| **난이도** | 쉬움 — 자연어로 바로 | 보통 — 스킬이 파이프라인 자동화 |
| **자동화/CI** | ❌ 불가 | ✅ 스크립트에 포함 가능 |
| **배치 생성** | ❌ | ✅ 여러 대시보드 루프 처리 |
| **리포트 타입** | 인사이트·펀넬·리텐션·플로우 | 인사이트·펀넬·리텐션 |

> MCP가 가능한 환경이라면 MCP 사용을 권장합니다.
> 자동화·CI·배치 처리가 필요할 때 이 스킬이 유용합니다.

---

## 기술 배경 — 왜 스킬이 필요했나

Mixpanel REST API의 `PATCH /dashboards/{id}` (layout 수정)는 항상 `500` 에러를 반환합니다.
대시보드에 리포트를 붙이는 유일한 방법은 MCP `Create-Dashboard` + `Run-Query` 파이프라인입니다.

핵심 발견 사항:
- `Run-Query`의 `dateRange`는 nested 구조: `{'type': 'relative', 'range': {'unit': 'week', 'value': 12}}`
- `Create-Dashboard` report row: `{'type': 'report', 'query_id': '...', 'name': '...'}`
- 텍스트 row: `html_content` (not `content`)
- 펀넬 `chartType`: `'steps'` (not `'funnel'`)
- MCP 응답은 SSE 형식 — `resp.json()` 금지, 라인별 파싱 필요
- `query_id`는 휘발성 — Run-Query 직후 Create-Dashboard 호출 필요
