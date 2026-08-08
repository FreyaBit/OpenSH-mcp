#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海图书馆开放数据 MCP —— Streamable HTTP 传输层（纯标准库，零第三方依赖）。

与 slc_mcp_server.py 共用同一套工具逻辑（handle_message / TOOLS / INSTRUCTIONS），
把 stdio 的 JSON-RPC 通过 HTTP 暴露为 Streamable HTTP（2025-03-26）端点，
供 Cursor / Claude / VS Code / WorkBuddy 等支持 http 类型 MCP 的客户端远程调用。

启动：
    python slc_mcp_http.py --port 8080
    # 或经统一入口： python slc_mcp_server.py --transport http --port 8080

客户端配置（Streamable HTTP）：
    {
      "mcpServers": {
        "shanghai-library-opendata": {
          "url": "http://127.0.0.1:8080/mcp"
        }
      }
    }

实现要点：
- POST /mcp  : 处理 JSON-RPC（单条或批量）。initialize 时签发 Mcp-Session-Id；
              通知类（notifications/*）返回 202 无响应体；请求返回 application/json。
- GET  /mcp  : SSE 流（server->client）。本服务不主动推送消息，仅保持连接存活（ping）。
- 支持 CORS（Access-Control-Allow-Origin: *），便于网页端 / 公网网关调用。
"""
import json
import os
import sys
import time
import uuid
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slc_mcp_server import handle_message, TOOLS, INSTRUCTIONS  # noqa: E402

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()


def _process_message(m):
    method = m.get("method") if isinstance(m, dict) else None
    if method and method.startswith("notifications/"):
        return None
    return handle_message(m)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ShanghaiLibraryOpenDataMCP/1.3.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, Mcp-Session-Id, Accept, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b"{}"
            msg = json.loads(raw or b"{}")
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        sid = self.headers.get("Mcp-Session-Id")
        is_init = isinstance(msg, dict) and msg.get("method") == "initialize"
        with SESSIONS_LOCK:
            if is_init or not sid or sid not in SESSIONS:
                sid = uuid.uuid4().hex
                SESSIONS[sid] = {}

        if isinstance(msg, list):
            results = [_process_message(m) for m in msg]
            payload = [r for r in results if r is not None]
            if not payload:
                self._respond_202(sid)
                return
        else:
            payload = _process_message(msg)
            if payload is None:
                self._respond_202(sid)
                return

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", sid)
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond_202(self, sid):
        self.send_response(202)
        self.send_header("Mcp-Session-Id", sid)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        # SSE 流：用于 server->client 消息。本服务不主动推送，仅保活。
        if urlparse(self.path).path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return
        sid = self.headers.get("Mcp-Session-Id", "")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        if sid:
            self.send_header("Mcp-Session-Id", sid)
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                time.sleep(15)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, *args):  # 静默
        pass


def run_http(host="127.0.0.1", port=8080):
    server = ThreadingHTTPServer((host, port), _Handler)
    sys.stderr.write(
        "上海图书馆开放数据 MCP (Streamable HTTP) 监听 "
        f"http://{host}:{port}/mcp\n")
    sys.stderr.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="上海图书馆开放数据 MCP (HTTP)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    run_http(a.host, a.port)
