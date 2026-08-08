#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海图书馆开放数据 MCP 服务（手写 stdio 协议，零第三方依赖）
工具清单：
  数据平台（data1.library.sh.cn，需 SLC_API_KEY）：
    slc_era / slc_jiapu / slc_building / slc_red_event
    slc_api          【通用分发器】调用 api_2025 注册的 99 个 webapi 接口
    slc_endpoints    列出全部可用接口（发现能力）
    slc_datasets / slc_sparql / slc_raw
  搜韵诗词（api.sou-yun.cn/open，免 token，服务 AIGC 歌曲）：
    souyun_poem / souyun_rhyme / souyun_couplet
依赖：仅标准库。Key 获取优先级：调用参数 key > 环境变量 SLC_API_KEY（mcp.json 的 env）。
代码内不含任何 Key，每个调用者传自己的 key 参数（环境变量或调用参数）。
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error

try:
    from slc_endpoints import ENDPOINTS
except Exception:
    ENDPOINTS = []

BASE = "https://data1.library.sh.cn"
SOUYUN = "https://api.sou-yun.cn/open"


def _env_key():
    """运行时读取环境变量 SLC_API_KEY（不在 import 时固定，支持长驻进程热更新）。"""
    return (os.environ.get("SLC_API_KEY") or "").strip()


def _load_dotenv():
    """从脚本同目录的 .env 读取 SLC_API_KEY（仅当环境变量未设置时）。
    纯标准库实现，零第三方依赖；.env 已被 .gitignore 忽略，不会入库泄露。"""
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.isfile(env_path) or os.environ.get("SLC_API_KEY"):
            return
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "SLC_API_KEY" and v:
                    os.environ.setdefault("SLC_API_KEY", v)
                    break
    except Exception:
        pass


_load_dotenv()


def _redact(text):
    """脱敏：抹掉文本中可能随请求 URL 携带的 key 值（key=...），避免错误回显泄露密钥。"""
    if not text:
        return text
    return re.sub(r"key=[^&\s\"']+", "key=***", text, flags=re.IGNORECASE)


def _resolve_key(a):
    """key 优先级：调用参数 key > 环境变量 SLC_API_KEY（代码内不存放任何 Key）。
    额外支持脚本同目录 .env 文件作为本地 Key 来源。"""
    return (a.get("key") or "").strip() or _env_key()


def _no_key():
    return json.dumps({"status": 400, "error": "缺少 APIKey：请传入 key 参数（填写你自己的上海图书馆开放数据 APIKey）"}, ensure_ascii=False)


def _http_req(method, url, data=None, headers=None):
    h = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "ignore")[:800]
        except Exception:
            body = ""
        return e.code, _redact(body)
    except Exception as e:
        return 0, _redact(repr(e))


def _http_get(url, accept="application/json"):
    return _http_req("GET", url, headers={"Accept": accept})


def slc_call(endpoint_id, params=None, path_args=None, key=None):
    params = params or {}
    path_args = path_args or []
    ep = next((e for e in ENDPOINTS if e["id"] == endpoint_id), None)
    if not ep:
        return 404, json.dumps({"error": "未知 endpoint", "hint": "用 slc_endpoints 查看可用 id"})
    try:
        path = ep["path"].format(*path_args) if path_args else ep["path"]
    except Exception as e:
        return 400, json.dumps({"error": "path_args 不足", "need": ep["path_params"], "detail": str(e)}, ensure_ascii=False)
    # ep["path"] 已是完整 URL（含 host），不要再拼 BASE；相对路径才拼
    base_url = path if path.startswith("http") else BASE + path
    method = ep.get("method", "GET").upper()
    q = dict(params)
    if ep.get("needs_key"):
        k = key or _env_key()
        if not k:
            return 400, _no_key()
        q["key"] = k
    if method == "POST":
        # POST 接口：查询参数走 JSON body；key 仍按文档放在 query 上
        body = json.dumps(params, ensure_ascii=False).encode("utf-8")
        post_url = base_url
        if ep.get("needs_key"):
            post_url += "?" + urllib.parse.urlencode({"key": key or _env_key()})
        return _http_req("POST", post_url, data=body,
                         headers={"Content-Type": "application/json"})
    url = base_url + "?" + urllib.parse.urlencode(q)
    return _http_req("GET", url)


def _wrap(status, text):
    try:
        return json.dumps({"status": status, "data": json.loads(text)}, ensure_ascii=False)
    except Exception:
        return json.dumps({"status": status, "text": text[:2000]}, ensure_ascii=False)


# ---------------- 工具实现 ----------------
def t_era(a):
    term = a.get("term", "")
    k = _resolve_key(a)
    if not k:
        return _no_key()
    url = BASE + "/data/" + urllib.parse.quote(term) + "?key=" + k
    s, t = _http_get(url)
    return _wrap(s, t)


def t_jiapu(a):
    k = _resolve_key(a)
    s, t = slc_call("work_data", {"title": a.get("title", ""), "familyname": a.get("familyname", "")}, key=k)
    return _wrap(s, t)


def t_building(a):
    k = _resolve_key(a)
    s, t = slc_call("building_list", {"freetext": a.get("keyword", "")}, key=k)
    return _wrap(s, t)


def t_red_event(a):
    kw = a.get("keyword", "")
    p = {"eventFreeText": kw} if kw else {"eventDate": a.get("date", "")}
    s, t = slc_call("route_getEventList", p, key=_resolve_key(a))
    return _wrap(s, t)


def t_api(a):
    eid = a.get("endpoint", "")
    if not any(e["id"] == eid for e in ENDPOINTS):
        fam = [e for e in ENDPOINTS if e.get("family") == eid]
        if fam:
            eid = fam[0]["id"]
        else:
            return json.dumps({"error": "endpoint 未找到", "hint": "用 slc_endpoints 查看可用 id"}, ensure_ascii=False)
    params = a.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    path_args = a.get("path_args") or []
    s, t = slc_call(eid, params, path_args, key=_resolve_key(a))
    return _wrap(s, t)


def t_endpoints(a):
    fam = a.get("family", "")
    items = [{"id": e["id"], "family": e["family"], "path": e["path"],
              "params": e["params"], "path_params": e["path_params"]}
             for e in ENDPOINTS if (not fam or e["family"] == fam)]
    return json.dumps({"count": len(items), "endpoints": items}, ensure_ascii=False)


def t_datasets(a):
    return json.dumps(DATASETS, ensure_ascii=False)


def t_sparql(a):
    note = ("该平台的 SPARQL JSON 结果被服务端拦截，仅网页端 https://data.library.sh.cn/sparql 可用。"
            "如需图查询，请在网页端验证语句后，用 slc_raw 调用其它 REST/webapi 接口。")
    return json.dumps({"status": "blocked", "note": note}, ensure_ascii=False)


def t_raw(a):
    path = a.get("path", "")
    params = a.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    k = _resolve_key(a)
    if not k:
        return _no_key()
    q = dict(params)
    q["key"] = k
    url = BASE + path + "?" + urllib.parse.urlencode(q)
    s, t = _http_get(url)
    return _wrap(s, t)


def t_poem(a):
    p = {"key": a.get("keyword", ""), "jsontype": "true"}
    for k in ("scope", "dynasty", "type", "rhyme"):
        if a.get(k):
            p[k] = a[k]
    if a.get("pageno"):
        p["pageno"] = a["pageno"]
    s, t = _http_get(SOUYUN + "/poem?" + urllib.parse.urlencode(p))
    return _wrap(s, t)


def t_rhyme(a):
    p = {"id": a.get("char", "")}
    if a.get("qtype") is not None:
        p["qtype"] = a["qtype"]
    s, t = _http_get(SOUYUN + "/rhymeDictionary?" + urllib.parse.urlencode(p))
    return _wrap(s, t)


def t_couplet(a):
    s, t = _http_get(SOUYUN + "/coupletwords?" + urllib.parse.urlencode({"id": a.get("word", "")}))
    return _wrap(s, t)


DATASETS = {
    "主题": "典籍新生，数据里的文脉风华",
    "方向": ["应用开发及智能体", "创意论文", "AIGC应用(微电影/歌曲/海报)"],
    "核心平台(需Key)": {
        "纪年/关联数据/SPARQL/内容协商": "data.library.sh.cn",
        "分类型 webapi(99个)": "data1.library.sh.cn，见 slc_endpoints",
    },
    "第三方机构(部分)": {
        "搜韵诗词(199万首/对仗300万)": "api.sou-yun.cn/open，免token，见 souyun_* 工具",
        "上海韬奋纪念馆": "zoutaofen 系列",
        "Artlib世界艺术鉴赏库": "17万幅美术图(需独立Key)",
        "CBDB中国历代人物传记": "64.9万人(离线ZIP)",
        "全国报刊索引": "晚清/民国期刊(需独立Key)",
    },
    "离线包": "上海图书馆开放数据2026.zip（含 API 文档/使用数据；大文化库走 API）",
}


# 所有工具均为「只读检索」，不修改任何远端数据，统一标注 annotations
def _ro(title):
    return {"title": title, "readOnlyHint": True, "openWorldHint": True}


# 通用 webapi 返回结构（由 _wrap 包裹）
_WRAP_OUT = {
    "type": "object",
    "description": "接口统一返回：status 为状态码，data 为解析后的 JSON，text 为非 JSON 时的原始文本",
    "properties": {
        "status": {"type": "integer", "description": "HTTP/业务状态码（200 表示成功）"},
        "data": {"type": "object", "description": "接口返回的 JSON 数据，具体结构随接口而异"},
        "text": {"type": "string", "description": "非 JSON 响应时的原始文本（已截断）"}
    }
}

# slc_endpoints 的返回结构
_EP_OUT = {
    "type": "object",
    "description": "接口清单：count 为数量，endpoints 为各接口元信息数组",
    "properties": {
        "count": {"type": "integer", "description": "可用接口数量"},
        "endpoints": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string", "description": "接口 id"},
            "family": {"type": "string", "description": "所属家族/分类"},
            "path": {"type": "string", "description": "接口路径模板"},
            "params": {"type": "object", "description": "支持的查询参数"},
            "path_params": {"type": "array", "items": {"type": "string"}, "description": "路径占位参数名"}
        }}}
    }
}

# slc_sparql 的返回结构
_SPARQL_OUT = {
    "type": "object",
    "description": "SPARQL 说明：status 恒为 blocked，note 为不可用原因与替代方案",
    "properties": {
        "status": {"type": "string", "description": "固定为 blocked"},
        "note": {"type": "string", "description": "说明与替代调用建议"}
    }
}

# slc_datasets 的返回结构
_DATASETS_OUT = {
    "type": "object",
    "description": "数据集与第三方机构总览，含主题、方向、核心平台、第三方机构与离线包说明",
    "properties": {
        "主题": {"type": "string"},
        "方向": {"type": "array", "items": {"type": "string"}},
        "核心平台(需Key)": {"type": "object"},
        "第三方机构(部分)": {"type": "object"},
        "离线包": {"type": "string"}
    }
}


def S(name, desc, props, required=None, output_schema=None, annotations=None):
    """构造一个工具描述，避免手写嵌套括号出错。"""
    sch = {"type": "object", "properties": props}
    if required:
        sch["required"] = required
    tool = {"name": name, "description": desc, "inputSchema": sch}
    if output_schema is not None:
        tool["outputSchema"] = output_schema
    if annotations is not None:
        tool["annotations"] = annotations
    return tool


TOOLS = [
    S("slc_era", "中国历史纪年表：输入朝代/年号返回公元年范围，或反之。例：明 -> 1368~1644。需传入 key（你自己的上海图书馆开放数据 APIKey）。",
      {"term": {"type": "string", "description": "朝代/年号/公元年，如 明、洪武、1369"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填，也可走环境变量 SLC_API_KEY）"}}, ["term"],
      output_schema=_WRAP_OUT, annotations=_ro("中国历史纪年检索")),
    S("slc_jiapu", "家谱谱目检索（data1 平台）：可按谱名或姓氏检索家谱。需传入 key。",
      {"title": {"type": "string", "description": "谱名关键词，如 王氏家谱"},
       "familyname": {"type": "string", "description": "姓氏，如 王"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填）"}},
      output_schema=_WRAP_OUT, annotations=_ro("家谱谱目检索")),
    S("slc_building", "武康路历史建筑检索（已验证可用）：按路名/建筑关键词检索。需传入 key。",
      {"keyword": {"type": "string", "description": "路名/建筑关键词，如 武康路"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填）"}}, ["keyword"],
      output_schema=_WRAP_OUT, annotations=_ro("历史建筑检索")),
    S("slc_red_event", "红色旅游/历史事件检索：按关键词或年份检索。需传入 key。",
      {"keyword": {"type": "string", "description": "事件关键词，如 中共一大会址"},
       "date": {"type": "string", "description": "年份，如 1940（与 keyword 二选一）"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填）"}},
      output_schema=_WRAP_OUT, annotations=_ro("红色旅游事件检索")),
    S("slc_api", "通用分发器：调用 api_2025 注册的全部 webapi 接口（家谱/古籍/盛档/人名库/碑帖/电影/期刊/舆图/书目/地名志/武康路 等 99 个）。endpoint 填接口 id；params 填查询参数(JSON)；path_args 填路径占位 {0}{1}；key 填你自己的上海图书馆开放数据 APIKey（必填）。先用 slc_endpoints 查 id。",
      {"endpoint": {"type": "string", "description": "接口 id 或 家族名（取该家族首个接口），如 work_data / 武康路历史"},
       "params": {"type": "object", "description": "查询参数（JSON 对象），如 {'freetext':'江南','pageNum':1}"},
       "path_args": {"type": "array", "items": {"type": "string"}, "description": "路径占位 {0}{1} 的取值列表"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填）"}}, ["endpoint"],
      output_schema=_WRAP_OUT, annotations=_ro("通用接口分发器")),
    S("slc_endpoints", "列出全部可用 webapi 接口（id/家族/路径/参数），可按 family 过滤。用于发现能力。",
      {"family": {"type": "string", "description": "可选：按家族过滤，如 古籍循证 / 武康路历史"}},
      output_schema=_EP_OUT, annotations=_ro("接口清单发现")),
    S("slc_datasets", "数据集与第三方机构总览：上海图书馆核心平台、搜韵诗词、韬奋纪念馆、Artlib、CBDB、全国报刊索引等。", {},
      output_schema=_DATASETS_OUT, annotations=_ro("数据集总览")),
    S("slc_sparql", "SPARQL 图查询说明：该平台 Key 仅网页端可用，本工具返回友好提示与替代方案而非报错。", {},
      output_schema=_SPARQL_OUT, annotations=_ro("SPARQL 说明")),
    S("slc_raw", "任意 data1.library.sh.cn 路径的 GET 兜底调用：当专属工具或 slc_api 不满足时使用。需传入 key。",
      {"path": {"type": "string", "description": "接口路径，如 /webapi/beitie/search"},
       "params": {"type": "object", "description": "查询参数（JSON 对象），如 {'freetext':'兰亭','pageNum':1}"},
       "key": {"type": "string", "description": "上海图书馆开放数据 APIKey（必填）"}}, ["path"],
      output_schema=_WRAP_OUT, annotations=_ro("原始接口兜底调用")),
    S("souyun_poem", "搜韵诗词检索（免 token）：按作者/标题/诗句/朝代/体裁/韵部查诗词，服务于 AIGC 歌词与创作。",
      {"keyword": {"type": "string", "description": "关键词或诗 ID，如 王之涣 / 登鹳雀楼 / 7734"},
       "scope": {"type": "string", "description": "检索范围：All / Author / Title / Sentence"},
       "dynasty": {"type": "string", "description": "朝代，如 Tang / Song"},
       "type": {"type": "string", "description": "体裁，如 QiLv / WuJue"},
       "rhyme": {"type": "string", "description": "韵部，如 江 / 尤"},
       "pageno": {"type": "integer", "description": "页码，从 1 开始"}}, ["keyword"],
      output_schema=_WRAP_OUT, annotations=_ro("搜韵诗词检索")),
    S("souyun_rhyme", "搜韵韵典（免 token）：查字所属韵部、词末/词首典故、句末诗例。",
      {"char": {"type": "string", "description": "韵字，如 天 / 月"},
       "qtype": {"type": "integer", "description": "0全部 1韵目 2词末典故 3词首 4词末 5句末诗例"}}, ["char"],
      output_schema=_WRAP_OUT, annotations=_ro("搜韵韵典")),
    S("souyun_couplet", "搜韵对仗词汇（免 token）：返回与输入字/词对仗的词汇，用于写对仗句。",
      {"word": {"type": "string", "description": "字或词，如 人间 / 月"}}, ["word"],
      output_schema=_WRAP_OUT, annotations=_ro("搜韵对仗词汇")),
]

HANDLERS = {
    "slc_era": t_era, "slc_jiapu": t_jiapu, "slc_building": t_building,
    "slc_red_event": t_red_event, "slc_api": t_api, "slc_endpoints": t_endpoints,
    "slc_datasets": t_datasets, "slc_sparql": t_sparql, "slc_raw": t_raw,
    "souyun_poem": t_poem, "souyun_rhyme": t_rhyme, "souyun_couplet": t_couplet,
}


INSTRUCTIONS = """\
上海图书馆开放数据 MCP —— 你的典籍与文脉数据助手。

你能做什么：
- 检索上海图书馆开放数据：中国历史纪年、家谱、武康路历史建筑、红色旅游事件、
  古籍循证、书目/人名/地名/舆图/碑帖/手迹/期刊/电影/音乐/照片等 99 个 webapi 接口，
  以及搜韵诗词（诗词检索、韵典、对仗词汇，免 token）。
- 用 slc_endpoints 发现全部可用接口；用 slc_api 通用分发任意接口；用 slc_raw 兜底调用。

怎么用（给调用你的 Agent）：
1. 需要 Key 的工具（slc_era / slc_jiapu / slc_building / slc_red_event / slc_api /
   slc_raw 及所有 data1 接口）：优先用环境变量 SLC_API_KEY；若未配置，调用时传 key 参数。
   Key 由使用者自己提供，切勿在返回内容里泄露他人 Key。
2. 不确定有哪些接口时，先调 slc_endpoints（可按 family 过滤）或 slc_datasets 总览。
3. slc_api 的 endpoint 填接口 id（先用 slc_endpoints 查）；params 填查询参数(JSON)；
   path_args 填路径占位 {0}{1}。
4. SPARQL 接口仅网页端 https://data.library.sh.cn/sparql 可用，本服务会返回友好提示而非报错。

注意事项：
- 不要臆造返回内容；接口失败时如实告知用户，必要时脱敏错误信息。
- 数据归属：结果请标注来源「上海图书馆开放数据」；第三方数据（如搜韵）按其许可注明。
- 高频调用请控制节奏，避免触发限流。
"""


def handle_message(req):
    """处理单条 JSON-RPC 请求，返回响应 dict；通知类（无 id）返回 None。"""
    if not isinstance(req, dict):
        return None
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}
    if method and method.startswith("notifications/"):
        return None
    if method == "initialize":
        pv = params.get("protocolVersion") or "2024-11-05"
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": pv,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "shanghai-library-opendata",
                "version": "1.3.2",
                "description": "上海图书馆开放数据 MCP：提供中国历史纪年、家谱、历史建筑、红色事件、99 个 webapi 接口，以及搜韵诗词（诗词检索/韵典/对仗词汇）的只读检索服务。"
            },
            "instructions": INSTRUCTIONS}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        handler = HANDLERS.get(name)
        if handler:
            try:
                out = handler(args)
            except Exception as e:
                out = json.dumps({"error": str(e)}, ensure_ascii=False)
        else:
            out = json.dumps({"error": "unknown tool"}, ensure_ascii=False)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": out}]}}
    return {"jsonrpc": "2.0", "id": rid, "result": {}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        out = handle_message(req)
        if out is None:
            continue
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def cli():
    """命令行入口：默认 stdio；--transport http 启动 Streamable HTTP 远程服务。"""
    import argparse
    ap = argparse.ArgumentParser(description="上海图书馆开放数据 MCP 服务")
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                    help="stdio（默认，本地子进程）或 http（Streamable HTTP 远程服务）")
    ap.add_argument("--host", default="127.0.0.1", help="http 模式监听地址")
    ap.add_argument("--port", type=int, default=8080, help="http 模式监听端口")
    args = ap.parse_args()
    if args.transport == "stdio":
        main()
    else:
        import slc_mcp_http
        slc_mcp_http.run_http(args.host, args.port)


if __name__ == "__main__":
    cli()
