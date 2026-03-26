# Mixpanel MCP vs CLI — 언제 무엇을 써야 하나

> 참고: [Mixpanel MCP 공식 문서](https://docs.mixpanel.com/docs/mcp) · [Mixpanel API Reference](https://developer.mixpanel.com/reference/overview)

---

## 왜 CLI가 필요한가? (MCP와 다른 점)

### 인증 방식의 차이

| | Mixpanel MCP | mixpanel-cli |
|---|---|---|
| 인증 | OAuth 2.0 (사용자 계정) | Service Account 또는 OAuth |
| 대시보드 수정 | ✅ 가능 | ✅ `auth login` 후 가능 |
| CI/자동화 | ❌ 불가 | ✅ 환경변수로 가능 |

MCP는 실제 사용자 OAuth 토큰으로 인증하기 때문에 대시보드 생성/수정이 가능합니다.
mixpanel-cli도 `mixpanel auth login`으로 동일한 OAuth 플로우를 지원합니다.

---

## MCP가 못하고 CLI만 할 수 있는 것

### 1. 파이프라인 / 자동화 조합

MCP는 Claude 대화 안에서만 동작합니다. **cron job, CI/CD, Shell 스크립트**에 넣을 수 없습니다.

```bash
# 배포 후 지표 자동 체크 (GitHub Actions)
- run: |
    mixpanel analytics insight --event "Error" \
      --from-date $(date +%Y-%m-%d) --to-date $(date +%Y-%m-%d) \
      --quiet | python check_error_spike.py

# 데이터 파이프라인
mixpanel export events --from-date 2026-01-01 --to-date 2026-03-31 \
  | jq 'select(.event == "Purchase")' \
  | python analyze.py \
  | aws s3 cp - s3://bucket/report.json
```

### 2. 대용량 데이터 로컬 저장

MCP는 응답 크기 한계와 토큰 비용 문제가 있습니다. CLI는 수백만 건도 파일로 스트리밍 저장합니다.

```bash
# 3개월치 Raw 데이터 스트리밍 저장 (30일 자동 청킹)
mixpanel export events \
  --from-date 2026-01-01 --to-date 2026-03-31 \
  --event-name "Purchase" \
  --file purchases.jsonl
```

### 3. 백그라운드 폴링 / 이상 감지 알림

MCP는 백그라운드 실행이 불가능합니다.

```bash
# 전환율 20% 이상 하락 시 슬랙 알림 — 24시간 백그라운드 실행
mixpanel watch \
  --event "Sign Up" \
  --threshold-drop 20 \
  --interval 60 \
  --webhook https://hooks.slack.com/xxx
```

### 4. 멀티 프로젝트 배치 작업

```bash
# 여러 프로젝트 지표 동시 비교
for project_id in 111 222 333; do
  mixpanel --project-id $project_id analytics insight \
    --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-31 \
    --quiet >> comparison.jsonl
done
```

### 5. Shell REPL — 반복 세션

```bash
mixpanel shell start
# > analytics insight --event "Sign Up" --from-date 2026-03-01 --to-date 2026-03-31
# > analytics funnel --id 123 --from-date 2026-03-01 --to-date 2026-03-31
# > ask query "전환율 왜 떨어졌지?"
# > use project 999999
```

MCP는 매번 Claude 대화가 필요합니다. REPL은 인증/설정을 유지한 채 연속 쿼리가 가능합니다.

### 6. 다른 CLI 도구와 조합

```bash
# Mixpanel 데이터 → BigQuery 적재
mixpanel export events --from-date 2026-03-01 --to-date 2026-03-31 --quiet \
  | bq load --source_format=NEWLINE_DELIMITED_JSON dataset.table -

# Mixpanel 데이터 → Slack 리포트
mixpanel analytics insight --event "Sign Up" --quiet \
  | jq '{text: "Sign Up: \(.data.values["Sign Up"])"}' \
  | curl -X POST -H 'Content-type: application/json' \
    --data @- https://hooks.slack.com/xxx
```

---

## 비개발자 유즈케이스

### 솔직한 평가

비개발자가 CLI 명령어를 직접 작성하는 시나리오는 현실적으로 낮습니다.
하지만 **Claude + CLI 조합**이 되면 완전히 달라집니다.

| 시나리오 | 현실성 |
|---------|--------|
| 비개발자가 CLI 명령어 직접 작성 | ❌ 낮음 |
| Claude에게 물어보고 명령어 복붙 실행 | ✅ 현실적 |
| `ask query`로 자연어 쿼리 | ✅ 높음 |
| Claude Code에서 AI가 CLI 직접 호출 | ✅ 가장 강력 |

### 페르소나별 시나리오

**마케터 — `ask` 명령으로 자연어 쿼리**

```bash
mixpanel ask query "이번 달 뉴스레터 구독 전환율이 지난달보다 높아?"
mixpanel ask query "3월에 데모 신청이 가장 많았던 요일은?"
mixpanel ask query "AI 플랫폼 유입 대비 기술블로그 유입 중 어디서 더 전환됐어?"
```

Mixpanel UI에서 직접 리포트 만드는 것보다 빠릅니다.

**PM / 기획자 — 정기 지표 추출**

```bash
# 주간 데이터 CSV로 뽑아 Excel/Sheets에 붙여넣기
mixpanel export events \
  --from-date 2026-03-17 --to-date 2026-03-23 \
  --event-name "Sign Up" \
  --file weekly_signups.jsonl
```

**마케터 — 전환율 이상 감지**

```bash
# 전환율이 20% 이상 떨어지면 슬랙 알림
# Claude가 명령어 작성 → 터미널에서 실행만
mixpanel watch \
  --event "데모 신청" \
  --threshold-drop 20 \
  --webhook https://hooks.slack.com/xxx
```

**Claude Code 조합 (가장 강력한 비개발자 시나리오)**

```
유저: "3월 전체 이벤트 데이터 뽑아서 데모 신청이 많았던 날의 공통점 분석해줘"

Claude: 1) mixpanel export 명령 실행
        2) 결과 데이터 분석
        3) 인사이트 정리해서 답변
```

CLI가 "AI의 Mixpanel 손"이 됩니다.

---

## 한 줄 요약

| | MCP | CLI |
|---|---|---|
| **강점** | 대화형 탐색, 즉석 분석, 컨텍스트 유지 | 자동화, 파이프라인, 대용량, 백그라운드 |
| **약점** | 자동화 불가, 토큰 비용 | 대화 맥락 없음 |
| **대상** | 탐색·의사결정 | 자동화·ETL·알림·배치 |

> MCP와 CLI는 대체재가 아니라 **보완재**입니다.
> MCP로 분석하고, CLI로 자동화하세요.
