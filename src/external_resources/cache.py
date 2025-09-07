from .checksums import get_checksum
from datetime import datetime as dt, UTC
import logging
import msgspec
from pathlib import Path
import sqlite3
# from uuid import uuid7  # use this from Python 3.14 onwards
from uuid_extensions import uuid7  # type: ignore[import-untyped]


logger = logging.getLogger("extres")


CACHE_DATABASE = "urls.db"
CACHE_CONTENTS = "files"
CACHE_DOWNLOAD = "downloads"


class CacheFileMetadata(msgspec.Struct):
    """Metadata for a cached resource file"""
    url: str
    size: int
    hash: str
    downloaded_at: dt


class ResourceCache(msgspec.Struct):
    """Holds metadata and access methods for the Resource Cache."""
    dir: Path
    db_conn: sqlite3.Connection | None = None
    db_data: dict[str, tuple[int, str, str]] = {}
    
    def make_conn(self) -> sqlite3.Connection:
        if self.db_conn is None:
            db_file = self.dir / CACHE_DATABASE
            self.db_conn = sqlite3.connect(db_file)
            logger.debug(
                    "connected to cache database %s",
                    db_file,
                    )
        return self.db_conn
    
    def close(self) -> None:
        if self.db_conn:
            self.db_conn.close()
    
    def read_db(self) -> None:
        conn = self.make_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("select * from urlhash")
        except sqlite3.OperationalError:
            cursor.execute("create table urlhash ("
                    "url string unique, "
                    "size int, "
                    "hash string, "
                    "created timestamp"
                    ")")
            self.db_data = {}
            logger.debug("created cache database table urlhash")
            return
        data: dict[str, tuple[int, str, str]] = {}
        count = 0
        for entry in cursor.fetchall():
            url, size, hash, created = entry
            data[url] = (size, hash, created)
            count += 1
        self.db_data = data
        cursor.close()
        logger.debug("%s records read from database", count)
    
    def get_metadata(self, url: str) -> CacheFileMetadata | None:
        if url in self.db_data:
            size, hash, created = self.db_data[url]
            md = CacheFileMetadata(url=url, size=size, hash=hash,
                    downloaded_at=dt.fromisoformat(created))
        else:
            md = None
        return md
    
    def get_filepath(self, url: str) -> Path | None:
        if url in self.db_data:
            size, hash, created = self.db_data[url]
            net_hash = hash.split(":", 1)[1]
            path = self.dir / CACHE_CONTENTS / net_hash
            if not path.exists():
                logger.warning(
                        "cache contents missing for %s",
                        url,
                        )
                return None
            return path
        return None
    
    def get_content(self, url: str) -> bytes | None:
        path = self.get_filepath(url)
        if path and path.exists():
            return path.read_bytes()
        return None
    
    def get_download_location(self) -> Path:
        """Returns target path for cache download."""
        temp_name = str(uuid7())
        download_dir = self.dir / CACHE_DOWNLOAD
        if not download_dir.exists():
            download_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        return download_dir / temp_name
    
    def add_to_cache(self,
            url: str,
            size: int,
            hash: str,
            data_file: Path,
            ) -> CacheFileMetadata:
        pure_hash = hash.split(":", 1)[1]
        content_dir = self.dir / CACHE_CONTENTS
        if not content_dir.exists():
            content_dir.mkdir(mode=0o700, exist_ok=True, parents=True)
        content_file = content_dir / pure_hash
        data_file.rename(content_file)
        
        tstamp = dt.now(UTC)
        tstamp_str = tstamp.isoformat()
        try:
            conn = self.make_conn()
            cursor = conn.cursor()
            cursor.execute(
                    "insert into urlhash values (?, ?, ?, ?)",
                    (url, size, hash, tstamp_str),
                    )
            cursor.close()
        except sqlite3.IntegrityError:
            logger.error(
                    "error when writing data for %s to cache: entry exists",
                    url,
                    )
            raise
        self.db_data[url] = (size, hash, tstamp_str)
        metadata = CacheFileMetadata(url=url, size=size, hash=hash,
                downloaded_at=tstamp)
        return metadata
