"""commands 패키지 내부 공통 유틸리티."""

from mixpanel_cli.auth.profile import AuthContext
from mixpanel_cli.client.mixpanel import MixpanelClient


def make_client(obj) -> tuple[MixpanelClient, AuthContext]:
    """AppContext에서 MixpanelClient와 AuthContext를 생성한다."""
    auth = AuthContext(
        profile_name=getattr(obj, "profile", "default"),
        project_id=getattr(obj, "project_id", None),
        region=getattr(obj, "region", None),
    )
    client = MixpanelClient(
        auth_header=auth.auth_header,
        project_id=auth.project_id,
        region=auth.region,
        timeout=getattr(obj, "timeout", 30),
        debug=getattr(obj, "debug", False),
    )
    return client, auth
