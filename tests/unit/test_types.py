"""types.py 단위 테스트."""

import pytest
import click
from click.testing import CliRunner
from mixpanel_cli.types import DATE, DateType


def test_date_valid():
    dt = DateType()
    result = dt.convert("2026-03-01", None, None)
    assert result == "2026-03-01"


def test_date_invalid_format():
    dt = DateType()
    with pytest.raises(click.exceptions.BadParameter):
        dt.convert("2026/03/01", None, None)


def test_date_invalid_short():
    dt = DateType()
    with pytest.raises(click.exceptions.BadParameter):
        dt.convert("26-03-01", None, None)


def test_date_in_cli():
    @click.command()
    @click.option("--from-date", "from_date", type=DATE)
    def cmd(from_date):
        click.echo(from_date)

    runner = CliRunner()
    result = runner.invoke(cmd, ["--from-date", "2026-03-01"])
    assert result.exit_code == 0
    assert "2026-03-01" in result.output

    result2 = runner.invoke(cmd, ["--from-date", "bad-date"])
    assert result2.exit_code != 0
