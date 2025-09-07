from datetime import datetime as dt
import msgspec
from pathlib import Path
from typing import cast, Self

from .cache import CacheFileMetadata
from .registry import RequiredResource


LF_VERSION = 1
LF_REVISION = 1
SUBDIRS = {"css": "css", "js": "js", "font": "fonts"}


def _make_local_path(
        name: str,
        type: str,
        vers_dir: str | None = None,
        ) -> str:
    """Sets the local destination path for a resource depending on its type."""
    dir_name = SUBDIRS[type]  # crash on mismatch for now
    if vers_dir is None:
        return f"{dir_name}/{name}"
    return f"{dir_name}/{vers_dir}/{name}"


class LockResFile(msgspec.Struct):
    url: str
    type: str
    destination: str
    hash: str | None = None
    size: int | None = None


class LockResMember(msgspec.Struct):
    name: str
    type: str
    destination: str


class LockResArchive(msgspec.Struct):
    url: str
    type: str
    hash: str | None = None
    size: int | None = None
    members: list[LockResMember] = []


class LockResource(msgspec.Struct):
    name: str
    version: str
    files: list[LockResFile] = []
    archives: list[LockResArchive] = []


class FileInfo(msgspec.Struct):
    lock_entry: LockResFile | LockResArchive
    resource_name: str
    version: str
    url: str
    is_cached: bool = False
    temp_filename: Path | None = None
    download_ok: bool = False
    download_status: int = 0
    error_message: str = ""
    size: int | None = None
    hash: str | None = None
    downloaded_at: dt | None = None
    data: bytes | None = None
    
    def update_from_cache(self, metadata: CacheFileMetadata) -> None:
        # compare with required settings XXX
        self.size = metadata.size
        self.lock_entry.size = self.size
        self.hash = metadata.hash
        self.lock_entry.hash = self.hash
        self.downloaded_at = metadata.downloaded_at
    
    def update_from_download(self, size: int, hash: str) -> None:
        self.size = size
        self.lock_entry.size = size
        self.hash = hash
        self.lock_entry.hash = hash


class LockFile(msgspec.Struct):
    version: int
    revision: int
    resources: list[LockResource] = []
    
    def make_fileinfo_list(self) -> list[FileInfo]:
        result: list[FileInfo] = []
        for res in self.resources:
            for f in res.files:
                fi = FileInfo(
                        lock_entry=f,
                        resource_name=res.name,
                        version=res.version,
                        url=f.url,
                        )
                result.append(fi)
            for f in res.archives:
                fi = FileInfo(
                        lock_entry=f,
                        resource_name=res.name,
                        version=res.version,
                        url=f.url,
                        )
                result.append(fi)
        return result
    
    @classmethod
    def from_requests(cls,
            reqs: list[RequiredResource],
            versioned_dir: str | None = None,
            ) -> Self:
        """Builds a LockFile structure from a list of required resources."""
        lf = cls(version=LF_VERSION, revision=LF_REVISION)
        
        for rr in reqs:
            res_item = rr.res_item
            res_version = res_item.versions[rr.version]
            lock_res = LockResource(name=rr.name, version=rr.version)
            for res_file in res_version.files:
                if res_file.is_archive():
                    lock_res_archive = LockResArchive(
                            url=res_file.url,
                            type=cast(str, res_file.type),
                            )
                    lock_res.archives.append(lock_res_archive)
                    for mem in res_file.members:
                        lock_res_mem = LockResMember(
                                name=mem.name,
                                type=mem.type,
                                destination=_make_local_path(
                                    name=mem.name,
                                    type=mem.type,
                                    vers_dir=versioned_dir,
                                    )
                                )
                        lock_res_archive.members.append(lock_res_mem)
                else:
                    lock_res_file = LockResFile(
                            url=res_file.url,
                            type=cast(str, res_file.type),
                            destination=_make_local_path(
                                name=res_file.local_name,
                                type=cast(str, res_file.type),
                                vers_dir=versioned_dir,
                                )
                            )
                    lock_res.files.append(lock_res_file)
            lf.resources.append(lock_res)
        return lf


def read_lockfile(filename: Path) -> LockFile:
    """Reads lockfile from disk."""
    lf = msgspec.toml.decode(
            filename.read_bytes(),
            type=LockFile,
            )
    return lf


def write_lockfile(filename: Path, data: LockFile) -> None:
    """Writes lockfile data to disk."""
    lf = msgspec.toml.encode(data)
    filename.write_bytes(lf)
