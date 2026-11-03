"""App drivers for the screen-tutorial pipeline (script-format.md § Actions).

`get_driver(name)` returns a driver instance for a script's `app` field.
"""

from .base import ACTIONS, Driver, DriverError  # noqa: F401

DRIVERS = {
    "excel": ".excel:ExcelDriver",
    "sheets": ".sheets:SheetsDriver",   # Google Sheets via Chrome (needs Accessibility; untested on device)
}


def get_driver(name, log=print):
    """Import and construct the driver for `app` (lazy, so tests need no app)."""
    if name not in DRIVERS:
        raise DriverError("no driver for app %r (have: %s)" % (name, ", ".join(sorted(DRIVERS))))
    module_name, cls_name = DRIVERS[name].split(":")
    import importlib
    module = importlib.import_module(module_name, __name__)
    return getattr(module, cls_name)(log=log)
