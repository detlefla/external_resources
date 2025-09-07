from collections import ChainMap
import msgspec
from packaging.requirements import Requirement
from packaging.version import parse as parse_version, Version
from pathlib import Path
from types import ModuleType
from typing import Literal
from urllib.parse import urlparse


class ResourceSpecificationError(ValueError):
    pass


def _get_dir_for_type(type: str) -> Path:
    """Determines subdirectory for file type."""
    res_dir: Path
    match type:
        case "css":
            res_dir = Path("css")
        case "js":
            res_dir = Path("js")
        case "font":
            res_dir = Path("fonts")
        case _:
            raise ResourceSpecificationError(f"unknown file type “{type}”")
    return res_dir


class ResourceMember(msgspec.Struct):
    type: Literal["css", "js", "font"]
    name: str
    comment: str = ""
    
    def get_local_filename(self) -> Path:
        """Returns relative target filename."""
        res_dir = _get_dir_for_type(self.type)
        local_name = self.name  # allow local_name to be different?
        return res_dir / local_name


class ResourceFile(msgspec.Struct):
    url: str
    local_name: str = ""
    comment: str = ""
    type: Literal["css", "js", "font", "zip"] | None = None
    integrity: str = ""
    members: list[ResourceMember] = []
    
    def is_archive(self) -> bool:
        """Indicates if this file is an archive file."""
        return self.type == "zip"
    
    def get_local_filename(self) -> Path:
        """Returns relative target filename."""
        if self.type is None:
            raise ResourceSpecificationError(
                    f"internal error: no resource type for “{self.url}”")
        res_dir = _get_dir_for_type(self.type)
        return res_dir / self.local_name


class ResourceVersion(msgspec.Struct):
    comment: str = ""
    files: list[ResourceFile] = []
    
    def local_filenames(self) -> list[Path]:
        """Returns list of filenames for local installation."""
        result: list[Path] = []
        for res_file in self.files:
            if res_file.is_archive():
                for res_member in res_file.members:
                    filename = res_member.get_local_filename()
                    result.append(filename)
            else:
                filename = res_file.get_local_filename()
                result.append(filename)
        return result


class VersionSpec(msgspec.Struct):
    version: Version
    res_version: ResourceVersion


class ResourceItem(msgspec.Struct):
    base_url: str = ""
    homepage: str = ""
    comment: str = ""
    versions: dict[str, ResourceVersion] = {}
    
    def version_list(self) -> list[str]:
        """Returns a list of available versions."""
        return list(self.versions.keys())


class RequiredResource(msgspec.Struct):
    name: str
    version: str
    res_item: ResourceItem
    extras: set[str]
    path_versioning: Literal["major", "minor"] | None
    
    def get_resource_version(self) -> ResourceVersion:
        """Returns ResourceVersion object pertaining to self's version."""
        return self.res_item.versions[self.version]


class Registry(msgspec.Struct):
    resources: dict[str, ResourceItem]
    
    def apply_requirements(
            self,
            requirements: list[str],
            versioned_paths: dict[str, Literal["major", "minor"]],
            with_prereleases: bool = False,
            ) -> list[RequiredResource]:
        """Applies a list of requirements to filter resource items and versions."""
        result: list[RequiredResource] = []
        for req in requirements:
            req_obj = Requirement(req)
            name = req_obj.name
            if name not in self.resources:
                raise ResourceSpecificationError(
                        f"external resource “{name}” is unknown")
            res_item = self.resources[name]
            avail_versions = res_item.version_list()
            usable_versions = list(req_obj.specifier.filter(
                    avail_versions,
                    prereleases=with_prereleases,
                    ))
            if not usable_versions:
                raise ResourceSpecificationError(
                        f"no suitable version for external resource “{name}”")
            version_specs = [
                    VersionSpec(
                        version=parse_version(version),
                        res_version=res_item.versions[version],
                        )
                    for version in usable_versions
                    ]
            version_specs.sort(key=lambda vs: vs.version)
            # most recent version is the last one
            best_version_spec = version_specs[-1]
            path_versioning = versioned_paths.get(name)
            res_req = RequiredResource(
                    name=name,
                    version=str(best_version_spec.version),
                    res_item=res_item,
                    extras=req_obj.extras,
                    path_versioning=path_versioning,
                    )
            result.append(res_req)
        return result


def inherit_vars(reg: Registry) -> None:
    """Determines inherited variable settings for all registry levels and formats."""
    # vars_list: list[dict[str, str]]
    vars: ChainMap[str, str] = ChainMap()
    for name, res_item in reg.resources.items():
        item_dict: dict[str, str] = dict(base_url=res_item.base_url, name=name)
        vars.maps.insert(0, item_dict)
        for version, res_version in res_item.versions.items():
            pv = parse_version(version)
            vers_dict: dict[str, str] = dict(
                    version=version,
                    major=str(pv.major),
                    minor=str(pv.minor),
                    patch=str(pv.micro),
                    epoch=str(pv.epoch),
                    )
            vars.maps.insert(0, vers_dict)
            for res_file in res_version.files:
                file_dict: dict[str, str] = dict(local_name=res_file.local_name)
                vars.maps.insert(0, file_dict)
                if "{" in res_file.url:
                    res_file.url = res_file.url.format(**vars)
                url = urlparse(res_file.url)
                if not res_file.local_name:
                    path = Path(url.path)
                    res_file.local_name = str(path.name)
                elif "{" in res_file.local_name:
                    res_file.local_name = res_file.local_name.format(**vars)
                if res_file.type is None:
                    suffix = Path(res_file.local_name).suffix
                    match suffix:
                        case ".js":
                            res_file.type = "js"
                        case ".css":
                            res_file.type = "css"
                        case ".ttf" | ".woff" | ".woff2" | ".pfb":
                            res_file.type = "font"
                        case ".zip":
                            res_file.type = "zip"
                        case _:
                            raise ValueError(
                                    f"unknown resource type “{suffix[1:]}” "
                                    f"for {name} version {version}"
                                    )
                del vars.maps[0]
            del vars.maps[0]
        del vars.maps[0]


def read_registry_file(filename: Path) -> Registry:
    """Reads a resource registry from a file (of type YAML, TOML or JSON)."""
    reader: ModuleType
    match suffix := filename.suffix:
        case ".yaml":
            reader = msgspec.yaml
        case ".toml":
            reader = msgspec.toml
        case ".json":
            reader = msgspec.json
        case _:
            raise ValueError(f"unknown resource registry file type “{suffix}”")
    reg = reader.decode(filename.read_bytes(), type=Registry)
    inherit_vars(reg)
    return reg
