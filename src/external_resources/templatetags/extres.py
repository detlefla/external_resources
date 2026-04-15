from django import template
from django.conf import settings
from django.utils.html import format_html, format_html_join
import logging
import msgspec
from pathlib import Path
from typing import cast

from ..lockfile import LockFile


class ResourceElement(msgspec.Struct):
    url: str
    module: bool = False
    deferred: bool = True


logger = logging.getLogger("django")
register = template.Library()
RESOURCES: dict[str, dict[str, list[ResourceElement]]] = dict(css={}, js={}, fonts={})
PROCESSED: list[bool] = []
SETTING_NAME = "EXTERNAL_RESOURCES_PATH"
LOCKFILE = "extres.lock"


def _get_resources() -> dict[str, dict[str, list[ResourceElement]]]:
    if PROCESSED:
        return RESOURCES
    path_setting = getattr(settings, SETTING_NAME, None)
    if path_setting is None:
        logging.warning("no setting for %s found", SETTING_NAME)
        return {}
    setting = cast(Path, path_setting)
    static = Path(settings.STATIC_URL) / "external"
    lock_file: LockFile = msgspec.toml.decode((setting / LOCKFILE).read_text(), type=LockFile)
    for res in lock_file.resources:
        for f in res.files:
            res_type = RESOURCES[f.type]
            url = static / f.destination
            if res.name not in res_type:
                res_type[res.name] = []
            res_type[res.name].append(ResourceElement(url=url))  # XXX module, defer
    PROCESSED.append(True)
    return RESOURCES


@register.simple_tag
def css_resource(name: str) -> str:
    res = _get_resources().get("css", {})
    files = res.get(name)
    if files is None:
        return ""
    args: list[str] = []
    for f in files:
        args.append({"url": f.url})
    result = format_html_join("\n",
            """<link href="{url}" rel="stylesheet" />""",
            args)
    return result


@register.simple_tag
def font_resource(name: str):
    res = _get_resources()
    rel_url = Path("fonts") / name  # XXX
    html = """ """
    return format_html(html, url=rel_url)


@register.simple_tag
def js_resource(name: str, defer: bool = True, module: bool = False):
    res = _get_resources().get("js", {})
    files = res.get(name)
    if files is None:
        return ""
    args: list[dict[str, str]] = []
    for f in files:
        args.append({
                "url": f.url,
                "deferred": "defer" if f.deferred else "",
                "module": "module" if f.module else "",
                })
    html = """<script src="{url}" {deferred} {module}></script>"""
    result = format_html_join("\n", html, args)
    return result
