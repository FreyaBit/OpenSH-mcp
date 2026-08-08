#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP 协议冒烟测试（精简版）：initialize / tools/list / 通用分发器 / 发现能力。
用法：SLC_API_KEY=你的上海图书馆开放数据 APIKey python3 tests/test_mcp.py
"""
import subprocess, json, os, sys

KEY = os.environ.get("SLC_API_KEY", "")
if not KEY:
    print("请先设置环境变量 SLC_API_KEY（你的上海图书馆开放数据 APIKey）")
    sys.exit(1)
env = dict(os.environ, SLC_API_KEY=KEY, PYTHONUNBUFFERED="1")
PY = sys.executable
p = subprocess.Popen([PY, "-u", "slc_mcp_server.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env, text=True)

def send(o):
    p.stdin.write(json.dumps(o, ensure_ascii=False) + "\n")
    p.stdin.flush()

def recv():
    return json.loads(p.stdout.readline())

try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    print("INIT:", recv().get("result", {}).get("serverInfo"))
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tl = recv()
    print("TOOLS(%d):" % len(tl["result"]["tools"]), [t["name"] for t in tl["result"]["tools"]])
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "slc_api", "arguments": {"endpoint": "work_data", "params": {"familyname": "王"}}}})
    print("GJ_API:", recv()["result"]["content"][0]["text"][:60])
    send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "slc_endpoints", "arguments": {}}})
    d = json.loads(recv()["result"]["content"][0]["text"])
    print("ENDPOINTS count:", d["count"])
finally:
    p.terminate()
    try:
        err = p.stderr.read(timeout=5)
    except Exception:
        err = "(读取 stderr 超时)"
    if err.strip():
        print("STDERR:", err[:400])
    print("DONE")
