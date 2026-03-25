"""shell REPL 모드 — 대화형 Mixpanel CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click

_HISTORY_FILE = Path.home() / ".mixpanel" / "history"
_BUILTIN_HELP = """\
내장 명령:
  use project <id>    현재 프로젝트 ID 변경
  use profile <name>  현재 프로파일 변경
  history             명령 히스토리 출력
  clear               화면 지우기
  exit / quit         REPL 종료
"""


@click.group("shell")
def shell_group():
    """대화형 REPL 모드."""
    pass


@shell_group.command("start")
@click.pass_context
def shell_start(ctx):
    """대화형 REPL 모드 시작."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.completion import WordCompleter
        _run_repl(ctx, PromptSession, FileHistory, AutoSuggestFromHistory, WordCompleter)
    except ImportError:
        click.echo(
            "[ERROR] prompt-toolkit 미설치. 다음을 실행하세요:\n"
            "  pip install mixpanel-cli[shell]",
            file=sys.stderr,
        )


def _run_repl(ctx, PromptSession, FileHistory, AutoSuggestFromHistory, WordCompleter):
    """REPL 루프 실행."""
    from mixpanel_cli.main import cli as root_cli

    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    completer = WordCompleter(
        [
            "analytics insight", "analytics funnel", "analytics retention", "analytics flow",
            "events list", "events get", "events properties",
            "export events",
            "project info", "project list",
            "ask query",
            "dashboard list", "dashboard get",
            "lexicon list",
            "use project", "use profile",
            "history", "clear", "exit", "quit", "help",
        ],
        ignore_case=True,
    )

    session = PromptSession(
        history=FileHistory(str(_HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
    )

    obj = ctx.obj
    project_id = getattr(obj, "project_id", None)
    profile = getattr(obj, "profile", "default")

    click.echo("Mixpanel REPL — 'exit' 또는 Ctrl+D로 종료. 'help' for commands.")

    while True:
        try:
            prompt = f"mixpanel({profile})> "
            line = session.prompt(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\n[shell] 종료")
            break

        if not line:
            continue

        # 히스토리 저장은 prompt_toolkit이 자동 처리
        tokens = line.split()
        cmd = tokens[0].lower() if tokens else ""

        if cmd in ("exit", "quit"):
            click.echo("[shell] 종료")
            break
        elif cmd == "help":
            click.echo(_BUILTIN_HELP)
        elif cmd == "clear":
            click.clear()
        elif cmd == "history":
            if _HISTORY_FILE.exists():
                click.echo(_HISTORY_FILE.read_text())
        elif cmd == "use" and len(tokens) >= 3:
            sub = tokens[1].lower()
            val = tokens[2]
            if sub == "project":
                project_id = val
                if obj:
                    obj.project_id = val
                click.echo(f"[shell] project → {val}")
            elif sub == "profile":
                profile = val
                if obj:
                    obj.profile = val
                click.echo(f"[shell] profile → {val}")
        else:
            # Click 명령으로 위임
            try:
                from click.testing import CliRunner
                runner = CliRunner(mix_stderr=False)
            except TypeError:
                from click.testing import CliRunner
                runner = CliRunner()
            args = tokens
            result = runner.invoke(root_cli, args, obj=obj, catch_exceptions=False)
            click.echo(result.output, nl=False)
