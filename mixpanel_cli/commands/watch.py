"""watch 명령 — 이벤트 지표 폴링 알림."""

from __future__ import annotations

import json
import sys
import time

import click
import httpx

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.types import DATE


@click.group("watch")
def watch_group():
    """이벤트 지표 폴링 및 임계값 알림."""
    pass


@watch_group.command("start")
@click.option("--event", required=True, help="모니터링할 이벤트 이름")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--interval", default=60, show_default=True, type=int, help="폴링 간격 (분)")
@click.option("--threshold-drop", "threshold_drop", default=None, type=float,
              help="이전 대비 하락 % 임계값 (예: 20 = 20% 하락 시 알림)")
@click.option("--threshold-rise", "threshold_rise", default=None, type=float,
              help="이전 대비 상승 % 임계값 (예: 50 = 50% 상승 시 알림)")
@click.option("--webhook", default=None, help="알림 전송할 Webhook URL")
@click.pass_context
def watch_start(ctx, event, from_date, to_date, interval, threshold_drop, threshold_rise, webhook):
    """이벤트 지표를 주기적으로 조회하고 임계값 초과 시 알림."""
    obj = ctx.obj
    prev_total: float | None = None

    click.echo(
        f"[watch] {event} 모니터링 시작 (간격: {interval}분). Ctrl+C로 종료.",
        file=sys.stderr,
    )

    try:
        while True:
            try:
                client, _ = make_client(obj)
                data = client.get_insight(
                    event=event,
                    from_date=from_date,
                    to_date=to_date,
                )
                total = _sum_insight(data)
                click.echo(
                    f"[watch] {event} = {total}",
                    file=sys.stderr,
                )

                if prev_total is not None and prev_total > 0:
                    change_pct = (total - prev_total) / prev_total * 100
                    _check_thresholds(
                        event, total, change_pct,
                        threshold_drop, threshold_rise, webhook,
                    )

                prev_total = total

            except MixpanelCLIError as e:
                click.echo(f"[watch] 오류: {e.message}", file=sys.stderr)

            time.sleep(interval * 60)

    except KeyboardInterrupt:
        click.echo("\n[watch] 종료", file=sys.stderr)


def _sum_insight(data: dict) -> float:
    """Insights 응답에서 총 이벤트 수 추출."""
    try:
        values = data.get("data", {}).get("values", {})
        total = 0.0
        for v in values.values():
            if isinstance(v, dict):
                total += sum(v.values())
        return total
    except Exception:
        return 0.0


def _check_thresholds(
    event: str,
    current: float,
    change_pct: float,
    threshold_drop: float | None,
    threshold_rise: float | None,
    webhook: str | None,
) -> None:
    """임계값 초과 시 stderr 출력 및 webhook 전송."""
    alert = None

    if threshold_drop is not None and change_pct <= -threshold_drop:
        alert = {
            "type": "drop",
            "event": event,
            "current": current,
            "change_pct": round(change_pct, 2),
            "threshold": threshold_drop,
            "message": f"[ALERT] {event} {change_pct:.1f}% 하락 (임계값: -{threshold_drop}%)",
        }
    elif threshold_rise is not None and change_pct >= threshold_rise:
        alert = {
            "type": "rise",
            "event": event,
            "current": current,
            "change_pct": round(change_pct, 2),
            "threshold": threshold_rise,
            "message": f"[ALERT] {event} +{change_pct:.1f}% 상승 (임계값: +{threshold_rise}%)",
        }

    if alert:
        click.echo(alert["message"], file=sys.stderr)
        if webhook:
            try:
                httpx.post(webhook, json=alert, timeout=10)
            except Exception as e:
                click.echo(f"[watch] webhook 전송 실패: {e}", file=sys.stderr)
