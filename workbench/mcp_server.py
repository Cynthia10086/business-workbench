#!/usr/bin/env python3
"""MCP stdio, newline-delimited JSON-RPC. No model/network connection.

Protocol references:
https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
https://modelcontextprotocol.io/specification/2025-06-18/server/tools
"""
import argparse
import json
import sys
from runtime import Workbench, WorkbenchError, dispatch, TOOLS

PROTOCOLS = ("2025-06-18", "2024-11-05")
MAX_LINE = 8 * 1024 * 1024


def rpc_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


class Server:
    def __init__(self, workbench):
        self.workbench = workbench
        self.initialized = False
        self.protocol = PROTOCOLS[0]

    def handle(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return rpc_error(None, -32600, "Invalid JSON-RPC request")
        if "id" not in request:
            return None
        id, method = request["id"], request["method"]
        if type(id) not in (str, int):
            return rpc_error(None, -32600, "Invalid request id")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return rpc_error(id, -32602, "Params must be an object")
        if method == "initialize":
            if not isinstance(params.get("protocolVersion"), str) or not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
                return rpc_error(id, -32602, "initialize requires protocolVersion, capabilities and clientInfo")
            self.initialized = True
            protocol = params["protocolVersion"] if params["protocolVersion"] in PROTOCOLS else PROTOCOLS[0]
            self.protocol = protocol
            result = {"protocolVersion": protocol, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "business-workbench-local", "version": "4.0.0"}, "instructions": "Operate only this explicit local workspace. Method records guide analysis; only user messages and source text can support business facts."}
        elif method == "ping":
            result = {}
        elif not self.initialized:
            return rpc_error(id, -32000, "Initialize before calling tools")
        elif method == "tools/list":
            if params.get("cursor"):
                return rpc_error(id, -32602, "This server does not paginate tools")
            result = {"tools": TOOLS}
        elif method == "tools/call":
            if not isinstance(params.get("name"), str) or not isinstance(params.get("arguments", {}), dict):
                return rpc_error(id, -32602, "tools/call requires a tool name and object arguments")
            try:
                data = dispatch(self.workbench, params["name"], params.get("arguments", {}))
                value, is_error = {"ok": True, "result": data}, False
            except WorkbenchError as exc:
                if exc.code in ("UNKNOWN_TOOL", "INVALID_ARGUMENT"):
                    return rpc_error(id, -32602, exc.code + ": " + exc.message)
                value, is_error = {"ok": False, "error": exc.as_dict()}, True
            except Exception:
                value, is_error = {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Local operation failed"}}, True
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, allow_nan=False)}], "isError": is_error}
            if self.protocol == "2025-06-18":
                result["structuredContent"] = value
        else:
            return rpc_error(id, -32601, "Method not found")
        return {"jsonrpc": "2.0", "id": id, "result": result}


def main():
    parser = argparse.ArgumentParser(description="Local MCP stdio server")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    try:
        with Workbench(args.workspace) as wb:
            server = Server(wb)
            while True:
                line = sys.stdin.buffer.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE:
                    # Drain just this oversized frame to preserve message framing.
                    while line and not line.endswith(b"\n"):
                        line = sys.stdin.buffer.readline(MAX_LINE + 1)
                    response = rpc_error(None, -32600, "Request exceeds 8 MiB frame limit")
                else:
                    try:
                        request = json.loads(line.decode("utf-8"))
                        response = server.handle(request)
                    except (ValueError, UnicodeError):
                        response = rpc_error(None, -32700, "Invalid UTF-8 JSON")
                if response is not None:
                    sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
                    sys.stdout.flush()
        return 0
    except WorkbenchError as exc:
        sys.stderr.write(exc.code + ": " + exc.message + "\n")
        return 2
    except OSError:
        sys.stderr.write("IO_ERROR: Cannot open local workspace\n")
        return 4


if __name__ == "__main__":
    sys.exit(main())
