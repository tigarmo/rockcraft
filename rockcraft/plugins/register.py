import craft_parts

from .python_plugin import RockcraftPythonPlugin


def register() -> None:
    craft_parts.plugins.register({"python": RockcraftPythonPlugin})
