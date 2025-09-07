import msgspec
from packaging.requirements import Requirement
from pathlib import Path
from typing import Literal

from .registry import Registry, RequiredResource, ResourceSpecificationError


TOOL_NAME = "external-resources"


class PyprojectData(msgspec.Struct, rename="kebab"):
    requires: list[str]
    versioned_paths: dict[str, Literal["major", "minor"]] = {}


class RequirementCollection(msgspec.Struct):
    requirements: dict[tuple[str, str], RequiredResource] = {}
    
    def add_req_resources(self, resources: list[RequiredResource]) -> None:
        """Adds result of Registry.apply_requirements to self."""
        for rr in resources:
            self.requirements[rr.name, rr.version] = rr
    
    def check_conflicts(self) -> None:
        """Checks for requirements with conflicting files."""
        names: set[str] = set()
        for rr in self.requirements.values():
            for filename in rr.get_resource_version().local_filenames():
                s_filename = str(filename)
                if s_filename in names:
                    raise ResourceSpecificationError(
                            f"filename conflict for “{s_filename}”")
                names.add(s_filename)

    def add_pyproject(self, registry: Registry, path: Path) -> None:
        """Adds requirements from a pyproject.toml file."""
        data = msgspec.toml.decode(path.read_bytes())
        if "tool" in data and TOOL_NAME in data["tool"]:
            tool_data = msgspec.convert(
                    data["tool"][TOOL_NAME],
                    type=PyprojectData,
                    )
            reqs = registry.apply_requirements(tool_data.requires,
                    versioned_paths=tool_data.versioned_paths)
            self.add_req_resources(reqs)
        else:
            print(f"no requirements for external resources found in {path}.")
