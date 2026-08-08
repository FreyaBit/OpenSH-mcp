#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 stdio JSON-RPC 测试：启动服务器进程，验证 initialize / tools/list / 真实 tools/call。
用法：SLC_API_KEY=你的上海图书馆开放数据 APIKey python3 tests/test_stdio.py
"""
import subprocess, json, os, sys

KEY = os.environ.get("SLC_API_KEY", "")
if not KEY:
    print("请先设置环境变量 SLC_API_KEY（你的上海图书馆开放数据 APIKey），例如：")
    print("  Windows PowerShell: $env:SLC_API_KEY='你的Key'; python tests/test_stdio.py")
    print("  macOS/Linux bash  : SLC_API_KEY='你的Key' python3 tests/test_stdio.py")
    sys.exit(1)

env = dict(os.environ, SLC_API_KEY=KEY, PYTHONUNBUFFERED="1")
PY = sys.executable
p = subprocess.Popen([PY, "-u", "slc_mcp_server.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env, text=True)

def send(o):
    p.stdin.write(json.dumps(o, ensure_ascii=False) + "\n"); p.stdin.flush()

def recv():
    return json.loads(p.stdout.readline())

try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    r = recv(); print("INIT serverInfo:", r["result"]["serverInfo"])
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    r = recv(); tools = r["result"]["tools"]
    print("TOOLS(%d):" % len(tools), [t["name"] for t in tools])
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "slc_building", "arguments": {"keyword": "武康路"}}})
    r = recv(); print("slc_building ->", r["result"]["content"][0]["text"][:80])
    send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
          "params": {"name": "souyun_poem", "arguments": {"keyword": "江南", "rhyme": "月"}}})
    r = recv(); print("souyun_poem ->", r["result"]["content"][0]["text"][:80])
    send({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
          "params": {"name": "slc_endpoints", "arguments": {"family": "武康路历史"}}})
    r = recv(); d = json.loads(r["result"]["content"][0]["text"])
    print("slc_endpoints(武康路历史) count:", d["count"])
finally:
    p.terminate()
    try:
        err = p.stderr.read(timeout=5)
    except Exception:
        err = "(读取 stderr 超时)"
    if err.strip():
        print("STDERR:", err[:400])
    print("DONE")
