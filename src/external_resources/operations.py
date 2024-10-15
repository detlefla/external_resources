import asyncio
import logging
from pathlib import Path
from typing import Any

from .cache import check_for_download, get_cache_subdir
from .resinfo import ResourceObject
from .tools import download_files


logger = logging.getLogger("extres")


def cmd_download(*, conf: dict[str, Any], resources: list[ResourceObject]) -> bool:
    """Manages downloads at command level."""
    dry_run = conf["dry_run"]
    force = conf["force"]
    verbose = conf["verbose"]
    dt: list[DownloadTask] = []
    for r in resources:
        get_cache_subdir(r, create=not dry_run)
        for it in r.release.item_list:
            check_for_download(r, it, dt, force=force)
    
    # start downloads
    ok = True
    if dry_run:
        for task in dt:
            print(task)
    else:
        asyncio.run(download_files(dt))
        if verbose:
            for task in dt:
                if task.ok:
                    print(f"OK {task.url} → {task.filename} ({task.size} bytes)")
                else:
                    ok = False
                    print(f"error for {task.url}:\n   {task.status_code} {task.message}")
    
    return ok
