#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海图书馆开放数据 MCP —— 一键安装脚本（给队友/协作者用）
用法：
  python setup_mcp_key.py
  或
  python setup_mcp_key.py --server "C:/路径/slc_mcp_server.py" --key "你的上海图书馆开放数据 APIKey"

功能：
  1. 把 MCP 服务写入 用户目录下的 ~/.workbuddy/mcp.json（已存在则合并，不覆盖其他服务器）
  2. Key 只存在使用者自己的机器上，绝不会随本脚本分发
注意：本脚本不含任何 Key，分享时请连同 slc_mcp_server.py 一起发给对方即可。
"""
import json
import os
import sys
import argparse

SERVER_NAME = "上海图书馆开放数据"
MCP_PATH = os.path.join(os.path.expanduser("~"), ".workbuddy", "mcp.json")


def find_default_python():
    # 优先用当前解释器，否则回退到 'python'
    return sys.executable or "python"


def main():
    ap = argparse.ArgumentParser(description="安装上海图书馆开放数据 MCP 到 WorkBuddy")
    ap.add_argument("--server", help="slc_mcp_server.py 的绝对路径")
    ap.add_argument("--key", help="你的上海图书馆开放数据 APIKey")
    args = ap.parse_args()

    server_path = args.server
    if not server_path:
        server_path = input("请粘贴 slc_mcp_server.py 的绝对路径：").strip().strip('"')
    key = args.key
    if not key:
        key = input("请粘贴你的上海图书馆开放数据 APIKey：").strip()

    if not server_path or not os.path.isfile(server_path):
        print("❌ 服务器脚本路径无效，请确认 slc_mcp_server.py 的位置。")
        sys.exit(1)
    if not key:
        print("❌ APIKey 不能为空。")
        sys.exit(1)

    # 读取已有配置（若有）
    config = {}
    if os.path.isfile(MCP_PATH):
        try:
            with open(MCP_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️ 已有 {MCP_PATH} 解析失败，将备份后重建：{e}")
            backup = MCP_PATH + ".bak"
            os.replace(MCP_PATH, backup)
            config = {}

    config.setdefault("mcpServers", {})
    config["mcpServers"][SERVER_NAME] = {
        "command": find_default_python(),
        "args": [server_path],
        "env": {"SLC_API_KEY": key},
        "disabled": False,
    }

    os.makedirs(os.path.dirname(MCP_PATH), exist_ok=True)
    with open(MCP_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ 已写入 {MCP_PATH}")
    print(f"   服务器名：{SERVER_NAME}")
    print("下一步：打开 WorkBuddy 连接器管理页 → 找到该服务器 → 点 Trust 启用。")


if __name__ == "__main__":
    main()
