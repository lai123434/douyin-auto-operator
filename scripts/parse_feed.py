#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析抖音推荐流视频卡片文本，归一化为结构化记录。

输入：从 bu.snapshot()/bu.get_page_text() 抓取的卡片原始文本（多条，每张卡片一段或多行）。
输出：JSON / 制表符分隔行，字段：title(标题) author(作者) posted(发布时间) duration(时长) hot(热度/点赞) link(链接,可选)。

用法（stdin 或文件）：
    python parse_feed.py < feed_dump.txt
    python parse_feed.py --file feed_dump.txt --json

说明：
- 卡片含 #话题、@作者、时长 mm:ss / hh:mm:ss、热度(如 14.0万 / 4539 / 2.3亿)。
- 解析尽力而为；无法识别的字段留空，不臆造。链接需由调用方从快照中的 href 补充。
"""
import argparse
import json
import re
import sys

# 时长：mm:ss 或 hh:mm:ss
_RE_DUR = re.compile(r"(\d{1,3}:\d{2}(?::\d{2})?)")
# 作者：@ 名字
_RE_AUTHOR = re.compile(r"@\s*([^\s·，,]+)")
# 发布时间：· xxx
_RE_POSTED = re.compile(r"·\s*([\d\w][\d\w天小时分秒前月日/年]*)")


def _parse_duration(text: str) -> str:
    m = _RE_DUR.search(text)
    return m.group(1) if m else ""


def _parse_author(text: str) -> str:
    m = _RE_AUTHOR.search(text)
    return m.group(1) if m else ""


def _parse_posted(text: str) -> str:
    m = _RE_POSTED.search(text)
    return m.group(1).strip() if m else ""


def _parse_hot(text: str) -> str:
    """热度：优先带 万/亿 后缀的数字；否则取数值最大的独立整数。
    排除紧跟 年月日前天小时分秒 等日期/时间单位后的数字（避免把标题里的数字误判）。"""
    t = _RE_DUR.sub("", text)  # 先去掉时长
    cands = re.findall(r"\d+(?:\.\d+)?[万亿]?", t)
    if not cands:
        return ""
    good = []
    for c in cands:
        idx = t.find(c)
        after = t[idx + len(c): idx + len(c) + 1] if idx >= 0 else ""
        if after and after in "年月日前天小时分秒":  # 空串不算，避免把行尾数字误跳过
            continue
        good.append(c)
    if not good:
        return ""
    wan = [g for g in good if g and g[-1] in "万亿"]
    if wan:
        return wan[0]
    return max(good, key=lambda g: float(g.rstrip("万亿")) if g else 0.0)


def _parse_title(text: str, hot: str, duration: str) -> str:
    """标题 = 原文本去掉发布时间、作者、时长、已识别的热度。"""
    t = re.sub(r"·\s*[\d\w][\d\w天小时分秒前月日/年]*", "", text)  # 发布时间（含前导·）
    t = re.sub(r"@\s*[^\s·，,]+", "", t)                          # 作者
    t = _RE_DUR.sub("", t)                                        # 时长
    if hot:
        t = t.replace(hot, "", 1)                                 # 热度（精确去掉，不误伤标题数字）
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_block(block: str) -> dict:
    text = block.strip()
    duration = _parse_duration(text)
    author = _parse_author(text)
    posted = _parse_posted(text)
    hot = _parse_hot(text)
    return {
        "title": _parse_title(text, hot, duration),
        "author": author,
        "posted": posted,
        "duration": duration,
        "hot": hot,
        "link": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="从文件读取卡片文本")
    ap.add_argument("--json", action="store_true", help="输出 JSON 数组")
    ap.add_argument("--sep", default="\t", help="非 JSON 输出的字段分隔符")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    blocks = [b for b in re.split(r"\n\s*\n", raw) if b.strip()]
    if not blocks and raw.strip():
        blocks = [raw.strip()]

    records = [parse_block(b) for b in blocks]

    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        print(args.sep.join(["title", "author", "posted", "duration", "hot", "link"]))
        for r in records:
            print(args.sep.join([r["title"], r["author"], r["posted"],
                                 r["duration"], r["hot"], r["link"]]))


if __name__ == "__main__":
    main()
