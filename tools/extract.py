#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《深入理解 AI Agent》PDF -> Markdown(含图表/表格截图),输出到 Docsify 站点。"""
import fitz, os, re, sys
from collections import Counter

PDF = "/Users/linweimin/Downloads/深入理解-AI-Agent-李博杰-v1.0.pdf"
SITE = "/Users/linweimin/codes/文档/agent-class"
OUT = os.path.join(SITE, "docs")
IMGDIR = os.path.join(OUT, "images")
os.makedirs(IMGDIR, exist_ok=True)

CHAPTERS = [
    ("00-引言", "引言", 9, 14),
    ("01-ai-agent-入门", "第 1 章 AI Agent 入门", 15, 34),
    ("02-上下文工程", "第 2 章 上下文工程", 35, 76),
    ("03-用户记忆和知识库", "第 3 章 用户记忆和知识库", 77, 106),
    ("04-工具", "第 4 章 工具", 107, 132),
    ("05-coding-agent-与代码生成", "第 5 章 Coding Agent 与代码生成", 133, 163),
    ("06-agent-的评估", "第 6 章 Agent 的评估", 164, 192),
    ("07-模型后训练", "第 7 章 模型后训练", 193, 232),
    ("08-agent-的自我进化", "第 8 章 Agent 的自我进化", 233, 249),
    ("09-多模态与实时交互", "第 9 章 多模态与实时交互", 250, 275),
    ("10-多agent-协作", "第 10 章 多 Agent 协作", 276, 304),
    ("11-后记", "后记：回到 Agent = LLM + 上下文 + 工具", 305, 307),
]

HEADER_Y = 70
FOOTER_Y = 780
GAP_SPACE = 2.0
GAP_SPACE_CODE = 1.5
IMG_ZOOM = 1.8

def is_alnum(ch):
    return bool(ch) and ord(ch) < 128 and ch.isalnum()

def clean_heading(text):
    return re.sub(r"\s+", " ", text).strip()

# ---------- 图表/表格检测 ----------
def count_columns(page, y0, y1):
    """媒体 y 区间内文本的对齐列数(>=2 行对齐算一列)。"""
    xs = sorted(round(w[0]) for w in page.get_text("words") if y0 <= w[1] <= y1)
    cols = []
    for x in xs:
        if not cols or x - cols[-1][-1] > 25:
            cols.append([x])
        else:
            cols[-1].append(x)
    return len([c for c in cols if len(c) >= 2])

def detect_media(page):
    """返回富媒体 y 包络 (y0,y1),无则 None。区分真图表/表格与装饰性 callout。"""
    graphic = []   # 含描边的真图形
    hlines = []    # 全宽水平细线(表格/分隔线)
    for d in page.get_drawings():
        r = d["rect"]
        w, h = r[2] - r[0], r[3] - r[1]
        if r[3] < HEADER_Y or r[1] > FOOTER_Y:
            continue
        if w > 500 and h > 760:
            continue
        if h < 2 and w > 300:
            hlines.append(r)
            continue
        if d.get("type") in ("s", "fs"):   # 描边(排除纯填充高亮/callout背景)
            graphic.append(r)
    ys = []
    # 图形触发:>=4 个描边元素(排除 1-2 条线的 callout/下划线)
    if len(graphic) >= 4:
        ys += [min(r[1] for r in graphic), max(r[3] for r in graphic)]
    # 表格触发:>=2 条全宽横线,且其间确有多列文本
    if len(hlines) >= 2:
        hy0, hy1 = min(r[1] for r in hlines), max(r[3] for r in hlines)
        if count_columns(page, hy0, hy1) >= 3:
            ys += [hy0, hy1]
    if not ys:
        return None
    y0, y1 = min(ys), max(ys)
    if y1 - y0 < 30:
        return None
    words = page.get_text("words")
    for wd in words:
        if y1 <= wd[1] <= y1 + 45 and (wd[4].startswith("图") or wd[4].startswith("表")):
            y1 = max(y1, max(ww[3] for ww in words if abs(ww[1] - wd[1]) < 4))
            break
    return (y0 - 12, y1 + 6)

# ---------- 文本行提取 ----------
def line_is_code(line):
    total = mono = 0
    for s in line["spans"]:
        t = s["text"].strip()
        if not t:
            continue
        total += len(t)
        if any(k in s["font"] for k in ("Menlo", "Mono", "Courier")):
            mono += len(t)
    return total > 0 and mono / total > 0.5

def render_line(line, code=False):
    spans = [s for s in line["spans"] if s["text"] != ""]
    if not spans:
        return ""
    spans.sort(key=lambda s: s["bbox"][0])
    buf, prev = "", None
    thresh = GAP_SPACE_CODE if code else GAP_SPACE
    for s in spans:
        t = s["text"]
        if "LatinModernMath" in s["font"]:
            t = t.replace("↪", "")
        if prev is not None:
            gap = s["bbox"][0] - prev["bbox"][2]
            if gap > thresh and not buf.endswith(" ") and not t.startswith(" "):
                buf += " "
        buf += t
        prev = s
    return buf.rstrip() if code else buf.strip()

def collect_lines(page, skip=None):
    skip = skip or []
    out = []
    d = page.get_text("dict")
    for b in d["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            y0 = l["bbox"][1]
            if y0 < HEADER_Y or y0 > FOOTER_Y + 15:
                continue
            if any(a <= y0 <= b2 for a, b2 in skip):   # 落在图表区,跳过
                continue
            spans = [s for s in l["spans"] if s["text"].strip()]
            if not spans:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            sz = max(s["size"] for s in spans)
            if line_is_code(l):
                txt = render_line(l, code=True)
                if txt.strip():
                    out.append(dict(y=y0, x0=x0, text=txt, size=sz, kind="code"))
                continue
            txt = render_line(l)
            if not txt:
                continue
            if sz >= 16.5:
                kind = "chapter"
            elif sz >= 13.0:
                kind = "h2"
            elif sz >= 11.0:
                kind = "h3"
            else:
                kind = "p"
            out.append(dict(y=y0, x0=x0, text=txt, size=sz, kind=kind))
    return out

def join_para(a, b):
    if not a:
        return b
    if a and b and is_alnum(a[-1]) and is_alnum(b[0]):
        return a + " " + b
    return a + b

def extract_chapter(doc, slug, title, p_start, p_end):
    # pass 1: 检测并渲染图表,收集每页行与图片
    all_pages = []
    xs = Counter()
    fig_idx = 0
    for pidx in range(p_start - 1, p_end):
        page = doc[pidx]
        media = detect_media(page)
        skip = [media] if media else []
        img_elem = None
        if media:
            y0, y1 = media
            clip = fitz.Rect(36, max(y0, 55), 560, min(y1, 800))
            pix = page.get_pixmap(matrix=fitz.Matrix(IMG_ZOOM, IMG_ZOOM), clip=clip)
            fname = f"{slug}_p{pidx + 1}.png"
            pix.save(os.path.join(IMGDIR, fname))
            fig_idx += 1
            img_elem = dict(y=y0, x0=0, text=f"images/{fname}", size=0, kind="image")
        lines = collect_lines(page, skip)
        if img_elem:
            lines.append(img_elem)
        lines.sort(key=lambda e: e["y"])
        all_pages.append(lines)
        for ln in lines:
            if ln["kind"] == "p":
                xs[round(ln["x0"])] += 1

    base = min([x for x, c in xs.most_common(5)]) if xs else 90

    md = [f"# {clean_heading(title)}\n"]
    para = code = None
    prev_x0 = None

    def flush_para():
        nonlocal para
        if para is not None and para.strip():
            md.append(para.strip() + "\n")
        para = None

    def flush_code():
        nonlocal code
        if code:
            md.append("\n```\n" + "\n".join(code).rstrip() + "\n```\n")
        code = None

    for lines in all_pages:
        for ln in lines:
            k = ln["kind"]
            if k == "code":
                flush_para(); prev_x0 = None
                if code is None:
                    code = []
                code.append(ln["text"])
                continue
            flush_code()
            if k == "image":
                flush_para(); prev_x0 = None
                md.append(f"\n![图]({ln['text']})\n")
            elif k == "chapter":
                continue
            elif k == "h2":
                flush_para(); prev_x0 = None
                md.append(f"\n## {clean_heading(ln['text'])}\n")
            elif k == "h3":
                flush_para(); prev_x0 = None
                md.append(f"\n### {clean_heading(ln['text'])}\n")
            else:
                x0 = ln["x0"]; indent = x0 - base
                if prev_x0 is None:
                    new_para = True
                elif x0 > prev_x0 + 6:
                    new_para = True
                elif 17 < indent < 23:
                    new_para = True
                else:
                    new_para = False
                if new_para:
                    flush_para(); para = ln["text"]
                else:
                    para = join_para(para or "", ln["text"]) if para is not None else ln["text"]
                prev_x0 = x0
    flush_code(); flush_para()
    return "\n".join(md)

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    doc = fitz.open(PDF)
    for slug, title, ps, pe in CHAPTERS:
        if only and only not in slug:
            continue
        text = extract_chapter(doc, slug, title, ps, pe)
        with open(os.path.join(OUT, slug + ".md"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"写入 {slug}.md  ({len(text)} 字符)")

if __name__ == "__main__":
    main()
