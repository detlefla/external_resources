import logging
import msgspec
import os
from pathlib import Path
from types import ModuleType
import xdg_base_dirs

from .registry import Registry, read_registry_file


APP_NAME = "external-resources"
CONFIG_FILENAME = "external_resources_config.yaml"


def _get_env_path(name: str) -> Path | None:
    """Tries to get a path name from an environment variable."""
    env_value = os.environ.get(f"EXTRES_{name.upper()}")
    if env_value is None:
        return None
    return Path(env_value)


class ConfigError(Exception):
    pass


class Config(msgspec.Struct):
    cache_dir: Path | None = None
    registry_path: Path | None = None
    lockfile: Path | None = None


class Options(msgspec.Struct):
    package_base: Path 
    working_dir: Path
    cache_dir: Path
    registry_path: Path
    registry_object: Registry
    config_file_path: Path | None = None
    config_object: Config | None = None
    lockfile_path: Path | None = None
    
    dry_run: bool = False
    debug: bool = False
    verbose: bool = False
    logger: logging.Logger | None = None


def _load_config(config_path: Path) -> Config:
    """Loads a configuration file."""
    module: ModuleType
    match suffix := config_path.suffix:
        case ".yaml":
            module = msgspec.yaml
        case ".toml":
            module = msgspec.toml
        case ".json":
            module = msgspec.json
        case _:
            raise ConfigError(f"unknown configuration file type “{suffix}”")
    config_object = module.decode(config_path, type=Config)
    return config_object


def get_options(
        dry_run: bool = False,
        debug: bool = False,
        verbose: bool = False,
        package_base: Path | None = None,
        working_dir: Path | None = None,
        registry_path: Path | None = None,
        config_file_path: Path | None = None,
        cache_dir: Path | None = None,
        lockfile_path: Path | None = None,
        ) -> Options:
    """Creates, initializes and returns Options object."""
    std_config_dir = xdg_base_dirs.xdg_config_home() / APP_NAME
    
    # create and initialize logger
    logger = logging.getLogger("extres")
    if debug:
        logger.setLevel(logging.DEBUG)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    logger.addHandler(logging.StreamHandler())
    
    # set working_dir if requested
    if working_dir is None:
        working_dir = _get_env_path("DIRECTORY")
    if working_dir is None:
        working_dir = Path.cwd()
    else:
        os.chdir(working_dir)
    
    # verify / determine package_base
    if package_base is None:
        package_base = _get_env_path("PACKAGE")
    if package_base is None:
        package_base = Path.cwd()
        while not (package_base / "pyproject.toml").exists():
            new_look_dir = package_base.parent
            if new_look_dir == package_base:
                raise ConfigError("no package directory (with pyproject.toml) found")
            package_base = new_look_dir
    else:
        if not (package_base / "pyproject.toml").exists():
            raise ConfigError("no pyproject.toml file found in “{package_base}”")
    
    # look for config file
    config_object: Config | None = None
    if config_file_path is None:
        config_file_path = _get_env_path("CONFIG")
    if config_file_path is None:
        config_dir = package_base
        while True:
            if (config_file_path := (config_dir / CONFIG_FILENAME)).exists():
                config_object = _load_config(config_file_path)
                break
            if config_dir.parent == config_dir:
                break
            config_dir = config_dir.parent
        if config_object is None:
            for extension in ".yaml", ".toml", ".json":
                if (config_file_path := (std_config_dir / f"config{extension}")).exists():
                    config_object = _load_config(config_file_path)
                    break
    else:
        config_object = _load_config(config_file_path)
    
    # look for registry, read it
    if registry_path is None:
        registry_path = _get_env_path("REGISTRY")
    if registry_path is None:
        if config_object is not None and config_object.registry_path is not None:
            registry_path = config_object.registry_path
        else:
            for filename in ("registry.yaml", "registry.toml", "registry.json"):
                if (registry_path := std_config_dir / filename).exists():
                    break
            else:
                raise ConfigError("no registry for external resources found")
    registry_object = read_registry_file(registry_path)
    logger.info("registry data loaded from “%s”", registry_path)
    
    # get cache dir
    if cache_dir is None:
        cache_dir = _get_env_path("CACHE_DIR")
    if cache_dir is None:
        if config_object is not None and config_object.cache_dir is not None:
            cache_dir = config_object.cache_dir
        else:
            cache_dir = xdg_base_dirs.xdg_cache_home() / APP_NAME
    if not cache_dir.exists():
        cache_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
        logger.info("created cache directory “%s”", cache_dir)
    
    # get lockfile location
    if lockfile_path is None:
        lockfile_path = _get_env_path("LOCKFILE")
    if lockfile_path is None:
        if config_object is not None and config_object.lockfile is not None:
            lockfile_path = config_object.lockfile
        else:
            lockfile_path = package_base / "extres.lock"
    
    # create and return Options object
    options = Options(
            package_base=package_base,
            working_dir=working_dir,
            registry_path=registry_path,
            registry_object=registry_object,
            config_file_path=config_file_path if config_object else None,
            config_object=config_object,
            cache_dir=cache_dir,
            lockfile_path=lockfile_path,
            dry_run=dry_run,
            debug=debug,
            verbose=verbose,
            logger=logger,
            )
    logger.debug("invocation options: %s\n", options)
    return options
