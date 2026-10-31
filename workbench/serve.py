#!/usr/bin/env python3
"""Optional loopback-only UI over the same Agent runtime. No model connection."""
import argparse
import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from runtime import Workbench, WorkbenchError, dispatch, TOOLS


def make_server(workspace, port=8770):
    token = secrets.token_hex(32)
    ui = (Path(__file__).parent / 'ui' / 'index.html').read_text(encoding='utf-8')
    allowed = {tool['name'] for tool in TOOLS} - {'knowledge_import'}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, data, mime='application/json; charset=utf-8'):
            body = data.encode('utf-8') if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def good_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.good_host():
                return self.send(403, {'ok': False, 'error': {'code': 'host_denied'}})
            if self.path == '/':
                return self.send(200, ui.replace('__SESSION_TOKEN__', token), 'text/html; charset=utf-8')
            return self.send(404, {'ok': False, 'error': {'code': 'not_found'}})

        def do_POST(self):
            if not self.good_host() or self.path != '/api/tool':
                return self.send(403, {'ok': False, 'error': {'code': 'request_denied'}})
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get('Origin') != origin or not hmac.compare_digest(self.headers.get('X-Session-Token', ''), token):
                return self.send(403, {'ok': False, 'error': {'code': 'origin_or_token_denied'}})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > 2_000_000:
                    return self.send(413, {'ok': False, 'error': {'code': 'payload_size'}})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or not isinstance(body.get('arguments', {}), dict):
                    raise ValueError('请求必须是对象')
                action, payload = body.get('name'), body.get('arguments', {})
                if action not in allowed or (action in {'source_add', 'taxonomy_get'} and 'path' in payload):
                    return self.send(403, {'ok': False, 'error': {'code': 'use_cli_for_file_access', 'message': '本地文件导入请使用 Agent 的 CLI / MCP 工具。'}})
                with Workbench(workspace) as wb:
                    result = dispatch(wb, action, payload)
                return self.send(200, {'ok': True, 'result': result})
            except WorkbenchError as error:
                return self.send(400, {'ok': False, 'error': {'code': error.code, 'message': error.message, 'details': error.details}})
            except (ValueError, TypeError, UnicodeDecodeError):
                return self.send(400, {'ok': False, 'error': {'code': 'invalid_request', 'message': '请求格式不正确。'}})
            except Exception:
                return self.send(500, {'ok': False, 'error': {'code': 'internal_error', 'message': '本地操作未完成，请查看工作目录或通过 CLI 诊断。'}})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--port', type=int, default=8770)
    args = parser.parse_args()
    with Workbench(args.workspace) as wb:
        dispatch(wb, 'workbench_init', {})
    server = make_server(args.workspace, args.port)
    print(f'Local workbench: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
