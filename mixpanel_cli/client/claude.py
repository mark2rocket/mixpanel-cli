"""Claude API 클라이언트 — ask 명령용 자연어 → Mixpanel 파라미터 변환."""

from __future__ import annotations

import json
import os
from typing import Any

from mixpanel_cli.exceptions import AINotInstalledError, RateLimitError

_SYSTEM_PROMPT = """\
You are a Mixpanel analytics expert. Given a natural language query and a list of available events,
return a JSON object with exactly these fields:
- "command": one of "insight", "funnel", "retention", "flow"
- "params": dict of parameters for the Mixpanel CLI command
- "summary_template": a concise English sentence template using {value} placeholder for the result
- "explanation": brief reason why you chose these parameters

For "insight" params: {"event": str, "from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD", "unit": "day"|"week"|"month"}
For "funnel" params: {"funnel_id": str, "from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD"}
For "retention" params: {"event": str, "from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD", "unit": "day"|"week"}
For "flow" params: {"event": str, "from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD"}

Today's date context will be provided. Return ONLY valid JSON, no markdown fences."""


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import keyring
        key = keyring.get_password("mixpanel-cli", "anthropic_api_key")
        if key:
            return key
    except Exception:
        pass
    raise AINotInstalledError(
        "ANTHROPIC_API_KEY not found. Set env var or run: "
        "keyring set mixpanel-cli anthropic_api_key"
    )


class ClaudeClient:
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self._api_key = _get_api_key()

    def ask_mixpanel(
        self,
        query: str,
        events: list[str],
        today: str,
    ) -> dict[str, Any]:
        """자연어 쿼리 → {command, params, summary_template, explanation} 딕셔너리 반환."""
        try:
            import anthropic
        except ImportError:
            raise AINotInstalledError(
                "anthropic package not installed. Run: pip install mixpanel-cli[ai]"
            )

        client = anthropic.Anthropic(api_key=self._api_key)
        user_msg = (
            f"Today: {today}\n"
            f"Available events: {json.dumps(events[:50])}\n\n"
            f"Query: {query}"
        )

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str:
                raise RateLimitError("Claude API rate limit 초과. 잠시 후 다시 시도하세요.")
            raise

        text = response.content[0].text.strip()
        # JSON 펜스 제거
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
