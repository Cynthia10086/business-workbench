"""Local operating reasoning workspace. Standard library only; no model or network."""
from .core import Workbench, WorkbenchError, dispatch
from .contract import TOOLS

__all__ = ["Workbench", "WorkbenchError", "dispatch", "TOOLS"]
