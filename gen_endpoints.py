#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 api_2025.txt 解析出全部 data1.library.sh.cn 接口，生成 slc_endpoints.py。"""
import re
import json
from collections import Counter

SRC = "api_2025.txt"
OUT = "slc_endpoints.py"

URL_RE = re.compile(r"https?://data1\.library\.sh\.cn[^\s]+")
PLACE = re.compile(r"[\[\{]参数\d+[\]\}]")

FAMILY = [
    ("service_pdf_race", "竞赛PDF文献"),
    ("zoutaofen", "韬奋纪念馆"),
    ("/webapi/kg/", "知识图谱人物"),
    ("whzk", "文化总库机构"),
    ("yutu", "舆图"),
    ("shouji", "手迹"),
    ("gmwx", "国漫革命文献"),
    ("/bib/webapi", "书目数据"),
    ("hsly", "红色旅游事件"),
    ("dmz", "地名志"),
    ("wkl", "武康路历史"),
    ("dydata", "近代城市文化"),
    ("/gj/webapi", "古籍循证"),
    ("/jp/", "家谱"),
    ("/persons/data", "人名规范库"),
    ("/place/", "地名纪年"),
    ("/data/", "纪年表关联数据"),
    ("/temporal", "纪年"),
    ("organization", "机构名录"),
    ("/data/jsonld", "JSON-LD关联"),
]


def fam(path):
    for kw, name in FAMILY:
        if kw in path:
            return name
    return "其他"


def norm(path):
    pp = []

    def repl(m):
        pp.append(m.group(0))
        return "{" + str(len(pp) - 1) + "}"

    return PLACE.sub(repl, path), pp


def main():
    text = open(SRC, encoding="utf-8").read()
    endpoints = {}
    for m in URL_RE.finditer(text):
        raw = m.group(0).rstrip("。，、）).；;")
        if "?" in raw:
            path, query = raw.split("?", 1)
        else:
            path, query = raw, ""
        path = path.rstrip("。，、）)")
        pt, pparams = norm(path)
        params = []
        if query:
            for part in query.split("&"):
                if "=" in part:
                    k = part.split("=", 1)[0].strip().lower()
                    if k and k != "key":
                        params.append(k)
        key = ("GET", pt)
        if key not in endpoints:
            seg = [s for s in pt.split("/") if s and not s.startswith("{")]
            eid = "_".join(seg[-2:]) if len(seg) >= 2 else (seg[0] if seg else "x")
            eid = re.sub(r"[^0-9a-zA-Z_]+", "_", eid).strip("_")
            endpoints[key] = {
                "id": eid, "method": "GET", "path": pt,
                "params": sorted(set(params)), "path_params": pparams,
                "family": fam(pt), "needs_key": True,
            }
        else:
            for p in params:
                if p not in endpoints[key]["params"]:
                    endpoints[key]["params"].append(p)
            endpoints[key]["params"].sort()

    reg = list(endpoints.values())
    # 解析每个接口真实的 HTTP 方法（请求方式：get/post），默认 GET。
    # 接口的“请求方式”可能出现在 URL 之前很远（URL 仅作为调用样例出现在后文），
    # 因此对每个 endpoint 取其在文档中【全局最近】的那条 请求方式。
    METHOD_RE = re.compile(r"请求方式[:：]\s*(get|post)", re.I)
    method_pos = [(m.start(), m.group(1).upper()) for m in METHOD_RE.finditer(text)]
    for r in reg:
        occ = [m.start() for m in re.finditer(re.escape(r["path"]), text)]
        if not occ:
            continue
        best_d, best_m = None, None
        for p in occ:
            for mp, mv in method_pos:
                d = abs(mp - p)
                if best_d is None or d < best_d:
                    best_d, best_m = d, mv
        if best_m:
            r["method"] = best_m
    seen = {}
    for r in reg:
        b = r["id"]
        i = 1
        while r["id"] in seen:
            r["id"] = f"{b}_{i}"
            i += 1
        seen[r["id"]] = True

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# 自动生成：上海图书馆开放数据 webapi 接口注册表（源自 api_2025.txt）\n")
        f.write("# id, method, path(含{0}{1}路径占位), params(查询参数), path_params, family, needs_key\n")
        f.write("ENDPOINTS = [\n")
        for r in reg:
            # 用 json.dumps 生成紧凑表示，但把 JSON 的 true/false/null 换成 Python 的 True/False/None
            s = json.dumps(r, ensure_ascii=False)
            s = re.sub(r"\b(true|false|null)\b",
                       lambda m: {"true": "True", "false": "False", "null": "None"}[m.group(0)],
                       s)
            f.write("    " + s + ",\n")
        f.write("]\n")
    print("生成", len(reg), "个接口 ->", OUT)
    for k, v in Counter(r["family"] for r in reg).most_common():
        print(f"  {v:3d}  {k}")


if __name__ == "__main__":
    main()
