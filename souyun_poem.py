#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜韵诗词数据 —— 歌词素材抓取工具（服务 AIGC 歌曲创作）
来源：搜韵网知识图谱 Web API（第三方诗词数据源）
文档：搜韵诗词数据开放接口开发指引 / 搜韵网知识图谱 Web API 开放接口

已实测：以下接口无需 token 即可调用（返回 application/json）。
  - 诗词检索   https://api.sou-yun.cn/open/poem
  - 韵典查询   https://api.sou-yun.cn/open/rhymeDictionary
  - 对仗词汇   https://api.sou-yun.cn/open/coupletwords
  - 韵目查询   https://api.sou-yun.cn/open/RhymeCategory
（知识图谱接口 open.cnkgraph.com 通常需 token，本模块未使用）

用法：
  from souyun_poem import collect_lyrics_material, search_poems
  pkg = collect_lyrics_material("江南", rhyme_char="月")   # 返回可直接喂给 AIGC 的素材包
  print(json.dumps(pkg, ensure_ascii=False, indent=2))
或命令行：
  python souyun_poem.py 江南 --rhyme 月
"""
import json
import urllib.parse
import urllib.request

POEM_BASE = "https://api.sou-yun.cn/open"


def _get(path: str, params: dict):
    clean = {k: v for k, v in params.items() if v is not None}
    url = POEM_BASE + path + "?" + urllib.parse.urlencode(clean)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def _text(node):
    """Title/Clauses 可能是 {'Content':...} 或字符串，统一取文本。"""
    if isinstance(node, dict):
        return node.get("Content") or node.get("content") or ""
    if isinstance(node, str):
        return node
    return ""


def search_poems(keyword, scope="All", dynasty=None, type_=None,
                 rhyme=None, pageno=0, jsontype=True):
    """按关键词检索诗词。
    scope:  All/Author/Title/Sentence(数字 0~3 亦可)
    dynasty: XianQin/Qin/Han/.../Tang/... 或数字 0~15
    type_:  体裁(如 QiLv 七律, WuJue 五绝...)
    rhyme:  韵部(如 江/尤)
    """
    params = {
        "key": keyword,
        "scope": scope,
        "jsontype": str(jsontype).lower(),
        "pageno": pageno,
    }
    if dynasty:
        params["dynasty"] = dynasty
    if type_:
        params["type"] = type_
    if rhyme:
        params["rhyme"] = rhyme
    return _get("/poem", params)


def get_poem(poem_id):
    """按诗 ID 取单首详情。"""
    return _get("/poem", {"key": poem_id, "jsontype": "true"})


def rhyme_dictionary(char, qtype=0, page_no=0):
    """韵典：查一个字所属韵部、词末/词首典故、句末诗例。
    qtype: 0查全部 1韵目 2词末典故 3词首 4词末 5句末诗例
    """
    return _get("/rhymeDictionary", {"id": char, "qtype": qtype, "pageNo": page_no})


def couplet_words(word):
    """对仗词汇：返回与输入字/词对仗的词汇参考列表。"""
    return _get("/coupletwords", {"id": word})


def rhyme_category(rhyme=None):
    """韵目查询：rhyme=None 返回平水韵总目；否则返回该韵下包含的字。"""
    if rhyme:
        return _get("/RhymeCategory", {"id": rhyme})
    return _get("/RhymeCategory", {"list": ""})


def collect_lyrics_material(theme, top_n=8, rhyme_char=None, dynasty=None, type_=None):
    """汇总一个「歌词素材包」，可直接作为 AIGC 作曲/作词工具的输入。

    返回结构：
      theme            主题词
      candidate_poems  候选诗词(标题/作者/朝代/体裁/韵部)
      candidate_lines  候选诗句(可直接化用作歌词)
      rhyme_suggestions 该主题下高频韵部(帮你选韵)
      couplet_words    若提供 rhyme_char，返回对仗词(帮写对仗句)
      allusions        若提供 rhyme_char，返回该字相关典故(帮写词)
    """
    poems = search_poems(theme, scope="All", dynasty=dynasty, type_=type_, pageno=0)
    shi = (poems.get("ShiData") or [])[:top_n]

    candidate_poems = []
    candidate_lines = []
    rhyme_count = {}
    for p in shi:
        title = _text(p.get("Title"))
        candidate_poems.append({
            "id": p.get("Id"),
            "title": title,
            "author": p.get("Author"),
            "dynasty": p.get("Dynasty"),
            "type": p.get("Type"),
            "rhyme": p.get("Rhyme"),
        })
        r = p.get("Rhyme")
        if r:
            rhyme_count[r] = rhyme_count.get(r, 0) + 1
        for c in (p.get("Clauses") or []):
            txt = _text(c)
            if txt:
                candidate_lines.append(txt)

    result = {
        "theme": theme,
        "candidate_poems": candidate_poems,
        "candidate_lines": candidate_lines,
        "rhyme_suggestions": rhyme_count,
    }
    if rhyme_char:
        result["couplet_words"] = couplet_words(rhyme_char)
        rd = rhyme_dictionary(rhyme_char, qtype=0)
        result["allusions"] = rd.get("Allusions") if isinstance(rd, dict) else None
    return result


def main():
    import argparse
    ap = argparse.ArgumentParser(description="搜韵诗词歌词素材抓取")
    ap.add_argument("theme", help="主题/意象关键词，如 江南 / 月 / 乡愁")
    ap.add_argument("--rhyme", help="可选：韵字，用于取对仗词与典故（如 月）")
    ap.add_argument("--dynasty", help="可选朝代，如 Tang")
    ap.add_argument("--type", help="可选体裁，如 QiLv")
    ap.add_argument("--top", type=int, default=8, help="候选诗词数量")
    args = ap.parse_args()
    pkg = collect_lyrics_material(args.theme, top_n=args.top,
                                  rhyme_char=args.rhyme, dynasty=args.dynasty, type_=args.type)
    print(json.dumps(pkg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
