import logging
import os
from pathlib import Path
from .resinfo import ResourceObject, ItemInfo
from .tools import DownloadTask, download_files


logger = logging.getLogger("extres")


def get_cache_dir() -> Path:
    """Returns the base dir for the resource cache."""
    env = os.environ.get("EXTRES_CACHE_DIR")
    if env:
        result = Path(env)
    else:
        result = Path("~/.cache") / "extres"
    result = result.expanduser()
    return result


def get_cache_subdir(res_obj: ResourceObject, create=False) -> Path:
    """Returns the directory path for all files of a resource."""
    cache_dir = get_cache_dir()
    subdir = cache_dir / res_obj.name / res_obj.version
    if create:
        subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def get_cache_path(res_obj: ResourceObject, item: ItemInfo) -> Path:
    """Returns the file path for a resource item."""
    cache_dir = get_cache_subdir(res_obj)
    typ = item.type or res_obj.variables.get("type", "unknown")
    filename = f"f-{typ}-{item.get_local_name(variables=res_obj.variables)}"
    return cache_dir / filename


def cache_file_exists(res_obj: ResourceObject, item: ItemInfo) -> bool:
    """Checks if cache file for this resource exists."""
    path = get_cache_path(res_obj, item)
    return path.exists()


def check_for_download(
        res_obj: ResourceObject,
        item: ItemInfo,
        downloads: list[DownloadTask],
        force=False):
    """Prepares download if cache file does not exist."""
    path = get_cache_path(res_obj, item)
    if path.exists() and not force:
        return
    dt = DownloadTask(item.get_full_url(variables=res_obj.variables), path)
    downloads.append(dt)
    return


def copy_files(res_obj_list: list[ResourceObject], target_base_path: Path):
    """Copies requested files to locations below the target_base_path."""
    downloads: list[DownloadTask] = []
    for res_obj in res_obj_list:
        check_for_download(res_obj, downloads)
    if downloads:
        download_files(downloads)
    for res_obj in res_obj_list:
        src = get_cache_path(res_obj)
        dst = res_obj.get_target_path(target_base_path)
        dst.write_bytes(src.read_bytes())
