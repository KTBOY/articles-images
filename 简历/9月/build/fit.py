# -*- coding: utf-8 -*-
"""Estimate rendered height / page count without a Word engine.

CJK glyph ~= 1 em wide, Latin/digit ~= 0.5 em. Line box ~= 1.2 * size * lineFactor.
A rough proxy, good enough to rank which paragraphs cost the most space.
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content import CN, EN  # noqa: E402

# kind -> (font size pt, line factor, before pt, after pt)
SPEC = {
    'name':   (17.0, 1.00, 0, 1.0),
    'tag':    (11.0, 1.00, 0, 1.0),
    'meta':   (9.0,  1.00, 0, 2.0),
    'h2':     (11.5, 1.00, 9.0, 3.5),
    'entry':  (10.0, 1.00, 5.0, 1.0),
    'sub':    (9.0,  1.00, 0, 2.0),
    'bullet': (9.5,  1.05, 0, 2.0),
    'body':   (10.0, 1.10, 0, 3.0),
}
PAGE_W = (11906 - 1000 - 1000) / 20.0   # 495.3 pt usable width
PAGE_H = (16838 - 720 - 720) / 20.0     # 769.9 pt usable height
BULLET_INDENT = 227 / 20.0              # pt lost to the bullet hang


def text_width_pt(s, size):
    w = 0.0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += size * 1.0
        elif ch == ' ':
            w += size * 0.28
        else:
            w += size * 0.52
    return w


def visible(text):
    """Strip our inline markup: [[label|url]] -> label, **bold** -> bold."""
    text = re.sub(r'\[\[([^\]|]+)\|?[^\]]*\]\]', r'\1', text)
    return text.replace('**', '')


def measure(blocks):
    rows, total = [], 0.0
    for kind, text in blocks:
        size, lf, before, after = SPEC[kind]
        avail = PAGE_W - (BULLET_INDENT if kind == 'bullet' else 0)
        w = text_width_pt(visible(text), size)
        lines = max(1, -(-w // avail))
        h = before + after + lines * size * 1.2 * lf
        rows.append((h, int(lines), kind, text))
        total += h
    return rows, total


if __name__ == '__main__':
    for label, blocks in (('中文版', CN), ('英文版', EN)):
        rows, total = measure(blocks)
        print('==== %s  估算高度 %.0fpt / 每页 %.0fpt => %.2f 页'
              % (label, total, PAGE_H, total / PAGE_H))
        rows.sort(reverse=True)
        print('  最占地方的 6 条：')
        for h, lines, kind, text in rows[:6]:
            print('    %5.1fpt %d行 [%s] %s' % (h, lines, kind, text[:46]))
        print()
