# -*- coding: utf-8 -*-
"""Static structural check for the generated resumes (no lxml available)."""
import os
import sys
import zipfile
import re
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'

PPR_SEQ = """pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers
pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN
bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc
textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange""".split()
STYLE_SEQ = """name aliases basedOn next link autoRedefine hidden uiPriority semiHidden unhideWhenUsed qFormat
locked personal personalCompose personalReply noKeepFollow pPr rPr tblPr trPr tcPr tblStylePr""".split()
LVL_SEQ = """lid start numFmt lvlRestart pStyle isLgl suffix lvlText lvlPicBulletId legacy lvlMapping
revision nesting algn pPr rPr""".split()
RPR_SEQ = """rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof
snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText
vertAlign rtl cs em lang eastAsianLayout specVanish oMath""".split()

fail = []


def q(tag):
    return tag.split('}')[-1]


def check_order(root, kind, seq, label):
    for el in root.iter():
        if q(el.tag) != kind:
            continue
        names = [q(c.tag) for c in el]
        idx = []
        for n in names:
            if n not in seq:
                fail.append('%s: unknown child <%s> in <%s>' % (label, n, kind))
                idx.append(-1)
            else:
                idx.append(seq.index(n))
        if idx != sorted(idx) or -1 in idx:
            fail.append('%s: bad child order in <%s>: %s' % (label, kind, ' '.join(names)))


def check(path):
    print('==== %s' % os.path.basename(path))
    z = zipfile.ZipFile(path)
    parts = {}
    for n in z.namelist():
        if n.endswith('.xml') or n.endswith('.rels'):
            try:
                parts[n] = ET.fromstring(z.read(n))
            except ET.ParseError as e:
                fail.append('%s: XML not well-formed: %s' % (n, e))
    print('  parts parsed: %d' % len(parts))

    doc = parts['word/document.xml']
    xml = z.read('word/document.xml').decode('utf-8')
    for forbidden, why in (('txbxContent', 'floating text box'),
                           ('<w:drawing', 'drawing object'),
                           ('<w:pict', 'pict object'),
                           ('<w:tbl>', 'table (breaks import order)')):
        c = xml.count(forbidden)
        print('  %-24s %d' % (forbidden, c))
        if c:
            fail.append('expected 0 %s, found %d' % (why, c))

    body = doc.find(W + 'body')
    cols = body.find(W + 'sectPr/' + W + 'cols')
    print('  columns: %s' % (cols.get(W + 'val') if cols is not None else 'MISSING'))
    if cols is None or cols.get(W + 'val') != '1':
        fail.append('sectPr must declare a single column')

    # hyperlinks resolve
    rels = parts['word/_rels/document.xml.rels']
    rmap = {r.get('Id'): (r.get('Target'), r.get('TargetMode')) for r in rels}
    used = [e.get(RNS + 'id') for e in doc.iter(W + 'hyperlink')]
    print('  hyperlinks: %d used / %d rels' % (len(used), len(rmap)))
    for rid in used:
        if rid not in rmap:
            fail.append('dangling hyperlink rId: %s' % rid)
        else:
            target, mode = rmap[rid]
            if mode != 'External' or not target.startswith('https://'):
                fail.append('bad hyperlink target: %s' % target)
    for rid, (target, mode) in rmap.items():
        if mode == 'External' and rid not in used:
            fail.append('unused hyperlink rel: %s -> %s' % (rid, target))

    # every run carrying visible text must sit in a paragraph with content
    empties = [p for p in body.iter(W + 'p') if not ''.join(
        t.text or '' for t in p.iter(W + 't')).strip()]
    if empties:
        fail.append('%d empty paragraphs' % len(empties))

    check_order(doc, 'pPr', PPR_SEQ, 'document')
    check_order(doc, 'rPr', RPR_SEQ, 'document')
    check_order(parts['word/styles.xml'], 'pPr', PPR_SEQ, 'styles')
    check_order(parts['word/styles.xml'], 'rPr', RPR_SEQ, 'styles')
    check_order(parts['word/styles.xml'], 'style', STYLE_SEQ, 'styles')
    check_order(parts['word/numbering.xml'], 'lvl', LVL_SEQ, 'numbering')

    n_p = len(list(body.iter(W + 'p')))
    print('  paragraphs: %d' % n_p)
    return z, body


def dump(path, limit=None):
    z = zipfile.ZipFile(path)
    body = ET.fromstring(z.read('word/document.xml')).find(W + 'body')
    out = []
    for p in body.findall(W + 'p'):
        style = p.find(W + 'pPr/' + W + 'pStyle')
        sid = style.get(W + 'val') if style is not None else 'Normal'
        txt = ''.join(t.text or '' for t in p.iter(W + 't'))
        mark = {'Bullet': '- ', 'SectionHeading': '## ', 'EntryHeader': '* ',
                'SubEntry': '  ', 'ResumeName': '# ', 'ResumeTag': '@ ',
                'MetaLine': '> ', 'Normal': '  '}.get(sid, '  ')
        out.append(mark + txt)
    return out[:limit] if limit else out


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [os.path.join(root, f) for f in sys.argv[1:]]
    for f in files:
        check(f)
    print('\n==== RESULT ====')
    if fail:
        for x in fail:
            print('FAIL: ' + x)
        sys.exit(1)
    print('all structural checks passed')
