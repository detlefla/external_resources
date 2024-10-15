import asyncio
from attrs import define
import httpx
import logging
from pathlib import Path


logger = logging.getLogger("extres")


@define
class DownloadTask:
    url: str
    filename: Path
    size: int | None = None
    ok: bool = False
    status_code: int = 0
    message: str | None = None


async def download(session: httpx.AsyncClient, task: DownloadTask):
    """Downloads a single resource."""
    logger.debug("Download starts for %s", task.url)
    response = await session.get(url=task.url)
    task.status_code = response.status_code
    task.ok = task.status_code == 200
    if task.ok:
        task.size = len(response.content)
        if task.filename != task.filename.parent:
            task.filename.write_bytes(response.content)
    else:
        task.message = f"status code {task.status_code} for {task.url}"
    logger.debug("Download finished for %s, size = %s", task.url, task.size)
    
    return

async def download_files(tasks: list[DownloadTask]):
    """Downloads a list of resources."""
    session = httpx.AsyncClient()
    await asyncio.gather(*[download(session, task) for task in tasks])
    await session.aclose()

if __name__ == "__main__":
    urls = [
            "https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js",
            "https://unpkg.com/vue@2.7.8/dist/vue.min.js",
            ]
    target = Path("/tmp/downloads")
    target.mkdir(exist_ok=True)
    tasks = [DownloadTask(url, target / url.split("/")[-1]) for url in urls]
    asyncio.run(download_files(tasks))
