"""JSON/CSV/table 출력 포매터."""

import csv
import io
import json
import sys
from typing import Any

import click

from mixpanel_cli.models import CLIResponse


def _to_json(data: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def _flatten(obj: Any, prefix: str = "") -> dict:
    """중첩 dict를 평탄화 (CSV 출력용)."""
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                result.update(_flatten(v, full_key))
            else:
                result[full_key] = v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            result.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        result[prefix] = obj
    return result


def _to_csv(data: Any) -> str:
    if isinstance(data, list):
        rows = [_flatten(item) for item in data]
    else:
        rows = [_flatten(data)]
    if not rows:
        return ""
    buf = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _to_table(data: Any) -> str:
    try:
        from rich.table import Table
        from rich.console import Console

        if isinstance(data, list):
            rows = [_flatten(item) for item in data]
        else:
            rows = [_flatten(data)]
        if not rows:
            return ""
        table = Table(show_header=True, header_style="bold")
        for col in rows[0].keys():
            table.add_column(str(col))
        for row in rows:
            table.add_row(*[str(v) for v in row.values()])
        buf = io.StringIO()
        console = Console(file=buf, highlight=False)
        console.print(table)
        return buf.getvalue()
    except ImportError:
        return _to_csv(data)


def print_response(
    response: CLIResponse,
    *,
    quiet: bool = False,
    pretty: bool = False,
    fmt: str = "json",
    no_color: bool = False,
) -> None:
    """CLIResponse를 stdout으로 출력. 상태/에러는 stderr."""
    if response.status == "error":
        error_obj = {
            "status": "error",
            "code": response.code,
            "message": response.message,
        }
        click.echo(_to_json(error_obj, pretty=pretty), file=sys.stdout)
        return

    if quiet:
        # data만 항상 유효한 JSON으로 출력
        click.echo(_to_json(response.data, pretty=False), file=sys.stdout)
        return

    if fmt == "csv":
        click.echo(_to_csv(response.data), file=sys.stdout)
    elif fmt == "table":
        click.echo(_to_table(response.data), file=sys.stdout)
    else:
        payload = response.model_dump(exclude_none=True)
        click.echo(_to_json(payload, pretty=pretty), file=sys.stdout)


def print_error(code: str, message: str, pretty: bool = False) -> None:
    """에러를 stdout으로 출력 (JSON 형식 유지)."""
    error_obj = {"status": "error", "code": code, "message": message}
    click.echo(_to_json(error_obj, pretty=pretty), file=sys.stdout)
