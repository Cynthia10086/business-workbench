#!/usr/bin/env python3
"""JSON command interface for local Agents. See --help and tools-list."""
import argparse
import json
from pathlib import Path
import sys
from runtime import Workbench, WorkbenchError, dispatch, TOOLS


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise WorkbenchError("INVALID_ARGUMENT", message)


def main(argv=None):
    parser = Parser(description="Local business workbench: no model configuration or network service.")
    parser.add_argument("--workspace", help="Explicit directory outside the product package")
    parser.add_argument("command", help="Tool name; tools-list prints the machine-readable command contract")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--payload", help="JSON object")
    group.add_argument("--payload-file", help="UTF-8 JSON argument file")
    try:
        args = parser.parse_args(argv)
        if args.command.replace("-", "_") == "tools_list":
            result = TOOLS
        else:
            if not args.workspace:
                raise WorkbenchError("INVALID_ARGUMENT", "--workspace is required")
            try:
                raw = Path(args.payload_file).read_text(encoding="utf-8-sig") if args.payload_file else (args.payload or "{}")
                payload = json.loads(raw)
            except (ValueError, UnicodeError):
                raise WorkbenchError("INVALID_JSON", "Payload must be valid UTF-8 JSON")
            with Workbench(args.workspace) as wb:
                result = dispatch(wb, args.command, payload)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except WorkbenchError as exc:
        print(json.dumps({"ok": False, "error": exc.as_dict()}, ensure_ascii=False))
        return 3 if exc.code in ("REVISION_CONFLICT", "KNOWLEDGE_CONFLICT", "LINEAGE_CONFLICT") else 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "IO_ERROR", "message": str(exc)}}, ensure_ascii=False))
        return 4
    except Exception:
        print(json.dumps({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Operation failed; original data was not intentionally overwritten."}}))
        return 5


if __name__ == "__main__":
    sys.exit(main())
