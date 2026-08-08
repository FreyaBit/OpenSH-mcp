#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海图书馆开放数据 —— RAG 知识库骨架（离线 ZIP + 实时 API 双源）
=================================================================
用途：把上海图书馆开放数据（离线包 / 实时接口返回）灌进一个可检索的知识库，
      供智能体做问答、做人物/历史叙事检索。

设计原则：
  * 检索核心【纯标准库】，零 ML 依赖，开箱即跑（中文用字+二元文法做词项，
    无需分词库即可获得可用的词法召回）。
  * 抽取层按文件类型适配：xlsx(openpyxl) / pdf(pypdf) / docx(python-docx) /
    txt·csv·tsv·tei·xml·json(stdlib) / rar(跳过并提示)。
  * 预留【接入真实向量库/嵌入模型】的钩子：见 ingest_items() 与文件末尾说明，
    生产环境可把 search() 换成 sentence-transformers + FAISS / chromadb。

CLI:
  python rag_kb.py build  --zip "上海图书馆开放数据2026.zip" --out kb.json
  python rag_kb.py search --kb kb.json --query "家谱 谱目" --top 5
"""
import json
import math
import os
import re
import sys
import zipfile

# ---------- 中文友好的词项化（字 + 二元文法，免分词库） ----------
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]+")


def tokenize(text):
    toks = []
    for m in re.findall(r"[A-Za-z0-9]+", text.lower()):
        toks.append(m)
    for run in _CJK.findall(text):
        if len(run) == 1:
            toks.append(run)
        else:
            for i in range(len(run)):
                toks.append(run[i])                 # 一元
                if i + 1 < len(run):
                    toks.append(run[i:i + 2])       # 二元
    return toks


def chunk_text(text, size=400, overlap=80):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out = []
    i = 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return out


# ---------- 抽取层 ----------
def _read_xlsx(path):
    try:
        import openpyxl
    except Exception:
        return "[xlsx] 需要 openpyxl：pip install openpyxl"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c) for c in r]
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            parts.append(f"[{ws.title}]\n" + "\n".join(rows))
    return "\n".join(parts)


def _read_pdf(path):
    try:
        from pypdf import PdfReader
    except Exception:
        return "[pdf] 需要 pypdf：pip install pypdf"
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception as e:
        return f"[pdf] 解析失败：{e}"


def _read_docx(path):
    try:
        import docx
    except Exception:
        return "[docx] 需要 python-docx：pip install python-docx"
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs if p.text.strip())


def _read_plain(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_file(name, data):
    """根据文件名/扩展名抽取文本。name 为 zip 内路径，data 为字节。"""
    low = name.lower()
    if low.endswith(".xlsx"):
        import tempfile
        p = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        p.write(data); p.close()
        t = _read_xlsx(p.name); os.unlink(p.name); return t
    if low.endswith(".pdf"):
        import tempfile
        p = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        p.write(data); p.close()
        t = _read_pdf(p.name); os.unlink(p.name); return t
    if low.endswith(".docx"):
        import tempfile
        p = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        p.write(data); p.close()
        t = _read_docx(p.name); os.unlink(p.name); return t
    if low.endswith((".txt", ".csv", ".tsv", ".tei", ".xml", ".json", ".sql", ".md")):
        return data.decode("utf-8", "ignore")
    if low.endswith(".rar"):
        return f"[rar] {name} 为压缩包，需 unrar/7z 解压后单独抽取（本骨架跳过）。"
    return ""


def iter_zip_text(zip_path):
    """生成 (source_name, text) 序列。"""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            try:
                data = z.read(info.filename)
                text = extract_file(info.filename, data)
                if text:
                    yield info.filename, text
            except Exception as e:
                yield info.filename, f"[抽取失败] {e}"


# ---------- 索引与检索 ----------
class RAGKB:
    def __init__(self):
        self.chunks = []          # {id, source, text}
        self.df = {}              # term -> 文档频
        self.N = 0
        self._tf = {}             # chunk_id -> {term: count}

    def add_document(self, source, text):
        for ch in chunk_text(text):
            self._add_chunk(source, ch)

    def _add_chunk(self, source, text):
        cid = len(self.chunks)
        self.chunks.append({"id": cid, "source": source, "text": text})
        tf = {}
        for t in tokenize(text):
            tf[t] = tf.get(t, 0) + 1
        self._tf[cid] = tf
        for t in tf:
            self.df[t] = self.df.get(t, 0) + 1
        self.N += 1

    def ingest_items(self, items, source, fields=None):
        """把结构化记录（如 API 返回的列表/字典）灌入知识库。
        items: list[dict] 或 list[str]
        fields: 指定参与索引的字段；为 None 时展平全部字段。"""
        for it in items:
            if isinstance(it, dict):
                if fields:
                    parts = [f"{k}: {it.get(k, '')}" for k in fields if k in it]
                else:
                    parts = [f"{k}: {v}" for k, v in it.items()]
                text = "\n".join(str(p) for p in parts)
            else:
                text = str(it)
            self.add_document(source, text)

    def _idf(self, term):
        return math.log((self.N + 1) / (self.df.get(term, 0) + 1)) + 1

    def search(self, query, top_k=5):
        qtf = {}
        for t in tokenize(query):
            qtf[t] = qtf.get(t, 0) + 1
        qvec = {t: c * self._idf(t) for t, c in qtf.items()}
        ql = math.sqrt(sum(v * v for v in qvec.values())) or 1

        cand = set()
        for t in qvec:
            for cid in self._tf:
                if t in self._tf[cid]:
                    cand.add(cid)
        scores = {}
        for cid in cand:
            tf = self._tf[cid]
            dot = sum(qvec[t] * (tf[t] * self._idf(t)) for t in qvec if t in tf)
            cl = math.sqrt(sum((tf[t] * self._idf(t)) ** 2 for t in tf)) or 1
            scores[cid] = dot / (cl * ql)
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [
            {"id": cid, "score": round(s, 4),
             "source": self.chunks[cid]["source"], "text": self.chunks[cid]["text"]}
            for cid, s in ranked
        ]

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"chunks": self.chunks, "df": self.df, "N": self.N,
                       "_tf": self._tf}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        kb = cls()
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        kb.chunks, kb.df, kb.N = d["chunks"], d["df"], d["N"]
        kb._tf = {int(k): v for k, v in d["_tf"].items()}  # JSON 键还原为 int
        return kb


def main():
    import argparse
    ap = argparse.ArgumentParser(description="上图开放数据 RAG 知识库骨架")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="从 ZIP 构建知识库")
    b.add_argument("--zip", required=True)
    b.add_argument("--out", default="kb.json")

    s = sub.add_parser("search", help="检索")
    s.add_argument("--kb", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    if args.cmd == "build":
        kb = RAGKB()
        n = 0
        for src, text in iter_zip_text(args.zip):
            kb.add_document(src, text)
            n += 1
        kb.save(args.out)
        print(f"已构建：{n} 个源文件，{kb.N} 个文本块 -> {args.out}")
    else:
        kb = RAGKB.load(args.kb)
        for r in kb.search(args.query, args.top):
            print(f"\n[score={r['score']}] {r['source']}\n{r['text'][:300]}")


if __name__ == "__main__":
    main()
