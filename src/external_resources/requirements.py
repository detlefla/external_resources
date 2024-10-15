from attrs import define, Factory
from cattrs.preconf.pyyaml import make_converter
import logging
from packaging.requirements import Requirement
from pathlib import Path
from pyproject_parser import PyProject
from typing import Any

from .resinfo import Resource


logger = logging.getLogger("extres")
CONFIG_FILE = "resources.yaml"
TOOL_NAME = "ext_resources"


@define
class Options:
    resources: dict[str, Resource] = Factory(dict)
    pyproject_path: Path | None = None
    tool_data: dict[str, Any] = Factory(dict)
    registry_path: Path | None = None


def read_file(filename: Path) -> dict[str, Resource]:
    converter = make_converter()
    values = converter.loads(filename.read_text(), dict[str, Resource])
    return values


def get_config(config_path: Path | None = None) -> dict[str, Resource]:
    result: dict[str, Resource] = {}
    if config_path is not None:
        result.update(read_file(config_path))
        logger.info("definitions of external resources loaded from %s", config_path)
    else:
        p: Path | None
        for p in [
                Path("/etc/extres") / CONFIG_FILE,
                (Path("~/.config/extres") / CONFIG_FILE).expanduser(),
                proj_path.parent / CONFIG_FILE if (proj_path := get_pyproject_path()) else None,
                ]:
            if p is not None and p.exists():
                result.update(read_file(p))
                logger.info("definitions of external resources loaded from %s", config_path)
    if not result:
        logger.warning("no definitions of external resources found")
    return result


def get_pyproject_path(start: str | Path = ".") -> Path | None:
    """Tries to locate a pyproject.toml file and to return its path."""
    p = Path(start).absolute()
    pp_path: Path | None = None
    while True:
        candidate = p / "pyproject.toml"
        if candidate.exists():
            pp_path = candidate
            break
        if p == p.parent:
            break
        p = p.parent
    return pp_path


def get_pyproject(pp_path: Path | None) -> PyProject:
    """Reads a pyproject.toml file."""
    if pp_path is None:
        raise FileNotFoundError("no pyproject.toml file found")
    pp = PyProject.load(pp_path)
    return pp


def get_tool_data(pp: PyProject, tool_name: str = TOOL_NAME) -> dict[str, Any]:
    """Gets data for this tool from pyproject.toml."""
    tool_data = pp.tool.get(tool_name)
    if tool_data is None:
        raise ValueError("tool data for ext_resources not found in pyproject.toml")
    return tool_data


def get_tool_reqs(tool_data: dict[str, Any]) -> list[Requirement]:
    """Gets requirements from a tool section within pyproject.toml."""
    return [Requirement(req) for req in tool_data["requires"]]


def read_requirements(start: str | Path = ".") -> list[Requirement]:
    """Gets requirements for this tool from pyproject.toml, located at “start” or above."""
    pp_path = get_pyproject_path(start)
    pp = get_pyproject(pp_path)
    td = get_tool_data(pp)
    reqs = get_tool_reqs(td)
    return reqs
