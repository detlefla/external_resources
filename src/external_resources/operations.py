import asyncio
import logging
import niquests
from pathlib import Path
import zipfile

from .cache import ResourceCache
from .checksums import get_checksum
from .lockfile import FileInfo, LockFile, write_lockfile
from .options import Options


logger = logging.getLogger("extres")


def _fill_cache(
        lf: LockFile,
        cache: ResourceCache,
        options: Options,
        ) -> list[FileInfo]:
    fi_list = lf.make_fileinfo_list()
    downloads: list[FileInfo] = []
    for fi in fi_list:
        md = cache.get_metadata(fi.url)
        if md is None:
            fi.temp_filename = cache.get_download_location()
            downloads.append(fi)
        else:
            fi.update_from_cache(md)
    
    download_files(downloads)
    
    errors_occurred = False
    for fi in downloads:
        if fi.download_ok and fi.data is not None:
            cache.add_to_cache(
                    url=fi.url,
                    size=fi.size,
                    hash=fi.hash,
                    data_file=fi.temp_filename,
                    )
        else:
            logger.error(
                    "download failed for %s (status: %s)",
                    fi.url,
                    fi.download_status,
                    )
            errors_occurred = True
    if errors_occurred:
        raise ValueError("download(s) failed")
    
    return fi_list


def lock_operation(
        lf: LockFile,
        cache: ResourceCache,
        options: Options,
        ) -> None:
    fi_list = _fill_cache(lf, cache, options)
    
    write_lockfile(
            options.lockfile_path,  # type: ignore[arg-type] # is never None
            lf,
            )


def _copy_or_link(from_path: Path, to_path: Path) -> None:
    if to_path.exists():
        # same data?
        # this method for finding out is not highly efficient :-(
        if from_path.read_bytes() == to_path.read_bytes():
            return  # nothing else to do
        else:
            logger.debug("removing existing file %s", to_path)
            to_path.unlink()
    try:
        to_path.hardlink_to(from_path)
    except OSError:
        # probable reason: crossing filesystem boundary
        to_path.write_bytes(from_path.read_bytes())


def sync_operation(
        target: Path,
        lf: LockFile,
        cache: ResourceCache,
        options: Options,
        ) -> None:
    fi_list = _fill_cache(lf, cache, options)
    
    for fi in fi_list:
        cache_path = cache.get_filepath(fi.url)
        if hasattr(fi.lock_entry, "destination"):
            target_path = target / fi.lock_entry.destination
            if not target_path.parent.exists():
                target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _copy_or_link(cache_path, target_path)
            logger.info("created resource at %s", target_path)
        elif has_attr(fi.lock_entry, "members"):
            zf = ZipFile(cache_path)
            zf_members = {
                    Path(name).name: name
                    for name in zf.namelist()
                    }
            for l_mem in fi.lock_entry.members:
                if l_mem.name in zf_members:
                    elem = zf_members[l_mem.name]
                    target_path = target / l_mem.destination
                    zf.extract(elem, path=target_path)
                    logger.info("created resource at %s", target_path)
                else:
                    logger.error(
                            "archive member %s not found in %s",
                            l_mem.name,
                            cache_path.name,
                            )
                            

async def download_a(
        s: niquests.AsyncSession,
        file_info: FileInfo,
        ) -> None:
    r = await s.get(file_info.url, stream=True)
    data = await r.content
    file_info.download_status = r.status_code
    if r.ok and data is not None and file_info.temp_filename is not None:
        # data should not be None if status == 200, only soothing the type checker
        # the temp_filename should never be None, only soothing the type checker
        file_info.download_ok = True
        file_info.update_from_download(size=len(data), hash=get_checksum(data))
        file_info.temp_filename.write_bytes(data)
        file_info.data = data
    else:
        file_info.download_ok = False
        print(f"{r.ok=}, {r.status_code=}, {r.history=}")
        print(f"data={repr(data):40}")
        print(file_info)
        file_info.error_message = f"get: status={r.status_code}, data={repr(data):40}"


async def download_files_a(
        file_info_list: list[FileInfo],
        ) -> None:
    async with niquests.AsyncSession() as s:
        await asyncio.gather(*[
                download_a(s, file_info)
                for file_info in file_info_list
                ])


def download_files(
        file_info_list: list[FileInfo],
        ) -> None:
    asyncio.run(download_files_a(file_info_list))
