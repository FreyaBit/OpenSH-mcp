#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过服务器自身的 handler 走一遍真实网络调用（GET + POST + 搜韵免 token）。
用法：SLC_API_KEY=你的上海图书馆开放数据 APIKey python3 tests/test_live.py
"""
import os, sys, json

KEY = os.environ.get("SLC_API_KEY", "")
if not KEY:
    print("请先设置环境变量 SLC_API_KEY（你的上海图书馆开放数据 APIKey）")
    sys.exit(1)
os.environ["SLC_API_KEY"] = KEY
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import slc_mcp_server as M

def show(label, text, n=140):
    print(f"\n[{label}]")
    try:
        d = json.loads(text)
        print("  status:", d.get("status"))
        s = json.dumps(d.get("data"), ensure_ascii=False)
        print("  data[:%d]:" % n, s[:n])
    except Exception:
        print("  raw[:%d]:" % n, text[:n])

show("slc_era(明)", M.t_era({"term": "明"}))
show("slc_building(武康路)", M.t_building({"keyword": "武康路"}))
show("slc_jiapu(王)", M.t_jiapu({"familyname": "王"}))
show("slc_red_event(1940)", M.t_red_event({"date": "1940"}))
show("slc_api(jp/work/data)", M.t_api({"endpoint": "work_data", "params": {"familyname": "王"}}))
show("slc_api(beitie_search POST)", M.t_api({"endpoint": "beitie_search", "params": {"freetext": "兰亭"}}))
show("slc_endpoints(count)", M.t_endpoints({}))
show("souyun_poem(王之涣)", M.t_poem({"keyword": "王之涣", "scope": "Author"}))
show("souyun_couplet(人间)", M.t_couplet({"word": "人间"}))
show("souyun_rhyme(月)", M.t_rhyme({"char": "月", "qtype": 1}))
