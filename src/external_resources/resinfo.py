from attrs import asdict, define, Factory
import logging
from packaging.requirements import Requirement
from packaging.specifiers import Specifier, SpecifierSet
from packaging.version import InvalidVersion, parse
from pathlib import Path
from typing import Any, Literal


logger = logging.getLogger("extres")
CONFIG_FILE = "resources.yaml"
INHERITED_ATTRS = ["base_url", "full_url", "local_name", "filename", "type"]
TypeLiterals = Literal["css"] | Literal["js"] | Literal["fonts"]


@define
class ItemInfo:
    full_url: str | None = None
    local_name: str | None = None
    filename: str | None = None
    type: TypeLiterals | None = None
    integrity: str | None = None
    archive: Literal["zip"] | None = None
    
    def get_full_url(self, variables) -> str:
        return (self.full_url or variables["full_url"]).format(**variables)
    
    def get_local_name(self, variables) -> str:
        if self.archive:
            # must have a filename attribute then XXX check
            return self.filename.format(**variables)
        return (self.local_name or variables["local_name"]).format(**variables)


@define
class Release:
    local_name: str | None = None
    filename: str | None = None
    base_url: str | None = None
    full_url: str | None = None
    item_list: list[ItemInfo] = Factory(list)
    integrity: dict[str, str] | None = None


@define
class Resource:
    releases: dict[str, Release]
    type: TypeLiterals
    versioning: Literal["std"] | Literal["none"] | Literal["dotted"] | Literal["numeric"] = "std"
    # optional attributes follow
    homepage: str | None = None
    comment: str | None = None
    filename: str | None = None
    base_url: str | None = None
    full_url: str | None = None
    local_name: str | None = None


@define
class ResourceObject:
    """Gathers resource information from the resource dict and a version specifier."""
    name: str
    resource: Resource
    version: str | None = None
    release: Release | None = None
    variables: dict[str, Any] = Factory(dict)
    
    def find_version(self, spec: SpecifierSet):
        """Returns the latest release version conforming to spec or None."""
        candidates = [(version, release)
                for (version, release) in self.resource.releases.items()
                if (spec is None) or (parse(version) in spec)
                ]
        if candidates:
            candidates.sort()
            version, release = candidates[-1]
            self.version = version
            self.release = release
        else:
            raise KeyError(f"Resource {self.name}: no release found for “{spec}”")
        
        for name in INHERITED_ATTRS:
            self.variables[name] = getattr(release, name, None) or getattr(self.resource, name)
            self.variables["version"] = version
            try:
                v = parse(version)
                self.variables["major"] = str(v.major)
                self.variables["minor"] = str(v.minor)
            except InvalidVersion:
                pass  # will raise an error if major or minor are referenced
        # print(self.name, self.variables)
    
    def get_full_url(self) -> str:
        return self.variables["full_url"].format(**self.variables)
    
    def get_local_name(self) -> str:
        return self.variables["local_name"].format(**self.variables)


def find_resources(
        resources: dict[str, Resource],
        requirements: list[Requirement],
        ) -> list[ResourceObject]:
    """Matches requirements against resources and returns a list of required resource objects."""
    result: list[ResourceObject] = []
    for req in requirements:
        resource = resources.get(req.name)
        if resource is None:
            raise KeyError(f"resource {req.name} is not defined")
        res_obj = ResourceObject(name=req.name, resource=resource)
        res_obj.find_version(spec=req.specifier)
        if not res_obj.release.item_list:
            res_obj.release.item_list.append(ItemInfo())
        
        result.append(res_obj)
    return result
