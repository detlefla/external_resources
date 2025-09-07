from cyclopts import App
import logging
from pathlib import Path

from .cache import ResourceCache
from .lockfile import LockFile, read_lockfile
from .operations import lock_operation, sync_operation
from .options import get_options
from .registry import read_registry_file
from .requirements import RequirementCollection


app = App()
logger = logging.getLogger("extres")


@app.command(show=False)
def test(
        package: Path | None = None,
        directory: Path | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        cache_dir: Path | None = None,
        registry: Path | None = None,
        ):
    options = get_options(
            dry_run=dry_run,
            debug=debug,
            verbose=verbose,
            package_base=package,
            working_dir=directory,
            registry_path=registry,
            cache_dir=cache_dir,
            )
    
    print(options)


@app.command(show=False)
def test_reg(
        requirements: list[str],
        package: Path | None = None,
        directory: Path | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        cache_dir: Path | None = None,
        registry: Path | None = None,
        ):
    """Test loading registry and applying requirements"""
    options = get_options(
            dry_run=dry_run,
            debug=debug,
            verbose=verbose,
            package_base=package,
            working_dir=directory,
            registry_path=registry,
            cache_dir=cache_dir,
            )
    import pprint
    import sys
    reg = read_registry_file(options.registry_path)
    pprint.pprint(reg)
    print()
    reqs = reg.apply_requirements(requirements, versioned_paths={})
    for req in reqs:
        pprint.pprint(req)
        pprint.pprint(req.get_resource_version())
        print()


@app.command(show=False)
def test_collect(
        registry: Path,
        pyproject_files: list[Path],
        ):
    """Test collecting requirements from several pyproject files"""
    import pprint
    import sys
    
    rc = RequirementCollection()
    reg = read_registry_file(registry)

    for fname in pyproject_files:
        print(f"reading {fname} …")
        rc.add_pyproject(reg, fname)
    print(rc)
    
    rc.check_conflicts()
    print()
    print("no conflicts detected")
    
    resources = list(rc.requirements.values())
    lf = LockFile.from_requests(resources)
    print()
    print(lf)
    
    print()
    for fi in lf.make_fileinfo_list():
        print(fi)


@app.command
def lock(
        requirements: list[str] = [],
        package: Path | None = None,
        directory: Path | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        cache_dir: Path | None = None,
        registry: Path | None = None,
        ):
    """Read requirements and write lockfile"""
    options = get_options(
            dry_run=dry_run,
            debug=debug,
            verbose=verbose,
            package_base=package,
            working_dir=directory,
            registry_path=registry,
            cache_dir=cache_dir,
            )
    
    rc = RequirementCollection()
    reg = read_registry_file(options.registry_path)
    rc.add_pyproject(reg, options.package_base / "pyproject.toml")
    if requirements:
        rc.add_req_resources(
                reg.apply_requirements(
                    requirements,
                    versioned_paths={},
                    ),
                )
    
    rc.check_conflicts()
    
    resources = list(rc.requirements.values())
    lf = LockFile.from_requests(resources)
    cache = ResourceCache(options.cache_dir)
    cache.read_db()
    
    lock_operation(lf, cache, options)
    
    cache.close()


@app.command
def sync(
        target: Path,
        package: Path | None = None,
        directory: Path | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        debug: bool = False,
        cache_dir: Path | None = None,
        registry: Path | None = None,
        ):
    """Read requirements and write lockfile"""
    options = get_options(
            dry_run=dry_run,
            debug=debug,
            verbose=verbose,
            package_base=package,
            working_dir=directory,
            registry_path=registry,
            cache_dir=cache_dir,
            )
    
    if not target.exists():
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        logger.info("target directory “%s” created", target)
    
    lf = read_lockfile(options.lockfile_path)
    cache = ResourceCache(options.cache_dir)
    cache.read_db()
    
    sync_operation(target, lf, cache, options)
    
    cache.close()
