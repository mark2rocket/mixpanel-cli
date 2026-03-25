"""Click 커스텀 타입."""

import re
import click


class DateType(click.ParamType):
    """YYYY-MM-DD 형식 날짜 검증."""

    name = "DATE"
    _pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def convert(self, value: str, param, ctx) -> str:
        if not self._pattern.match(value):
            self.fail(
                f"날짜 형식이 올바르지 않습니다: '{value}'. YYYY-MM-DD 형식을 사용하세요.",
                param,
                ctx,
            )
        return value


class RegionType(click.Choice):
    """리전 선택 타입."""

    def __init__(self):
        super().__init__(["us", "eu", "in"], case_sensitive=False)


DATE = DateType()
REGION = RegionType()
