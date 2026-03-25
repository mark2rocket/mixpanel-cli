"""export 명령 그룹."""

import sys
import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.output.formatter import print_error
from mixpanel_cli.types import DATE


@click.group("export")
def export_group():
    """Raw 이벤트 데이터 내보내기."""
    pass


@export_group.command("events")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--event-name", default=None, help="특정 이벤트만 필터")
@click.option("--file", "output_file", default=None, help="저장할 JSONL 파일 경로 (미지정 시 stdout)")
@click.option("--timeout", default=30, show_default=True, type=int, help="HTTP 타임아웃 (초)")
@click.pass_context
def export_events(ctx, from_date, to_date, event_name, output_file, timeout):
    """Raw 이벤트 JSONL 내보내기 (자동 30일 청킹)."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    if obj and obj.timeout != 30:
        timeout = obj.timeout

    try:
        client, _ = make_client(obj)
        total_bytes = 0

        if output_file:
            with open(output_file, "wb") as f:
                for chunk in client.export_events(
                    from_date=from_date,
                    to_date=to_date,
                    event_name=event_name,
                ):
                    f.write(chunk)
                    total_bytes += len(chunk)
            click.echo(
                f"[export] 완료: {output_file} ({total_bytes:,} bytes)",
                file=sys.stderr,
            )
        else:
            # stdout으로 스트리밍
            for chunk in client.export_events(
                from_date=from_date,
                to_date=to_date,
                event_name=event_name,
            ):
                sys.stdout.buffer.write(chunk)
                total_bytes += len(chunk)
            click.echo(f"[export] 완료: {total_bytes:,} bytes", file=sys.stderr)

    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
    except IOError as e:
        print_error("IO_ERROR", str(e), pretty=pretty)
