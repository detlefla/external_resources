#! /usr/bin/env python3

from cyclopts import App, Parameter
import logging
from packaging.requirements import Requirement, InvalidRequirement
from pathlib import Path
import subprocess
import sys
from typing import Annotated

from .cache import check_for_download, get_cache_path, get_cache_subdir
from .operations import cmd_download
from .requirements import get_config, read_requirements
from .resinfo import find_resources, Resource

logger = logging.getLogger("extres")
CONFIG_FILE = "ext_resources.yaml"

# Application instance, to be invoked if called directly or through package entry point
app = App()


@app.command
def download(
        *requirements: str,
        force: bool = False,
        config_file: Path | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        ):
    conf = get_config(config_file)
    conf["dry_run"] = dry_run
    conf["verbose"] = verbose
    conf["force"] = force
    
    if requirements == ("all",):
        reqs = []
        for name, r in conf.items():
            if not isinstance(r, Resource):
                continue
            for version in r.releases.keys():
                try:
                    r = Requirement(f"{name}=={version}")
                except InvalidRequirement:
                    r = f"{name}=={version}"
                reqs.append(r)
    elif requirements:
        reqs = [Requirement(r) for r in requirements]
    else:
        reqs = read_requirements()
    res = find_resources(conf, reqs)

    
    ok = cmd_download(conf=conf, resources=res)
    
    if not ok:
        print("Aborted!")
        sys.exit(1)


@app.command
def install(
        *requirements: str,
        target_path: Path = Path("static_external/external"),
        config_file: Path | None = None,
        download: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
        ):
    """Install the specified resources (default: all that are required by pyproject.toml)"""
    conf = get_config(config_file)
    conf["dry_run"] = dry_run
    conf["verbose"] = verbose
    conf["force"] = False
    target_path = target_path.expanduser().absolute()
    
    if requirements:
        reqs = [Requirement(r) for r in requirements]
    else:
        reqs = read_requirements()
    res = find_resources(conf, reqs)
    
    if download:
        ok = cmd_download(conf=conf, resources=res)
    else:
        ok = True
    
    if not ok:
        print("Aborted!")
        sys.exit(1)
    
    # start copying
    for r in res:
        for it in r.release.item_list:
            cache_path = get_cache_path(r, it)
            typ = it.type or r.variables.get("type", "unknown")
            target_dir = target_path / typ
            target = target_dir / it.get_local_name(r.variables)
            if dry_run:
                print(f"\ncp {cache_path} {target}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                # XXX check if copying is necessary?!
                out = subprocess.check_output(["cp", cache_path, target])
                if verbose:
                    print(f"copied: {cache_path}\n        → {target}")


#@app.command
def deploy(
        *,
        source: str,
        destination: str,
        delete: bool = False,
        index: str = "external_resources.yaml",
        config_file: Annotated[str, Parameter(
            help="configuration file (YAML), default: use config in pyproject.toml")] = "",
        dry_run: bool = False,
        verbose: bool = False,
        ):
#    with open(config_file) as f:
#        options = yaml.safe_load(f)
#    ctx = dict(external_resources=options)
    # deploy_resources(ctx, source=source, destination=destination, delete=delete, dry_run=dry_run)
    return 0


#@app.command
def check(
        name: str,
        *,
        static_dir: str = "static",
        index: str = "external_resources.yaml",
        config_file: Annotated[str, Parameter(
            help="configuration file (YAML), default: use config in pyproject.toml")] = "",
        verbose: bool = False,
        ) -> int:
#    try:
#        if config_file:
#            with open(config_file) as f:
#                opt = yaml.safe_load(f)
#        else:
#            opt = Options.from_pyproject(index=index, verbose=verbose)
#        _check_resource(opt, name=name, static=static_dir)
#    except Exception as e:
#        rprint(f"[red]command error {e}")
#        return 1
    return 0


if __name__ == "__main__":
    app()
