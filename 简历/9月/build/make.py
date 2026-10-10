# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content import CN, EN, OUT  # noqa: E402
from docx_gen import build  # noqa: E402

cn_path = os.path.join(OUT, '周淋朝（Web前端开发）-中文修正版.docx')
en_path = os.path.join(OUT, 'Linchao-Zhou-Frontend-Developer-Upwork.docx')

build(CN, cn_path, '周淋朝 - Web 前端开发工程师', '周淋朝')
build(EN, en_path, 'Linchao Zhou - Frontend Developer', 'Linchao Zhou')

for p in (cn_path, en_path):
    print(os.path.basename(p), os.path.getsize(p), 'bytes')
