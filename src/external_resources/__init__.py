from importlib.resources import files

__version__ = (files(__name__) / "VERSION" ).read_text().strip()
