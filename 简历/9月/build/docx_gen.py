import re
import zipfile
import html
import os

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CONTENT_W = 9906  # A4 11906 - 1000 - 1000


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


TOKEN = re.compile(r'(\*\*[^*]+\*\*|\[\[[^\]]+\]\])')


def inline(text, rels):
    """Render a paragraph's runs. Supports **bold** and [[label|url]]."""
    out = []
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            out.append(
                '<w:r><w:rPr><w:b/></w:rPr>'
                '<w:t xml:space="preserve">%s</w:t></w:r>' % esc(part[2:-2])
            )
        elif part.startswith('[[') and part.endswith(']]'):
            body = part[2:-2]
            if '|' in body:
                label, url = body.split('|', 1)
            else:
                label = url = body
            rid = 'rId%d' % (100 + len(rels))
            rels.append((rid, url))
            out.append(
                '<w:hyperlink r:id="%s">'
                '<w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
                '<w:t xml:space="preserve">%s</w:t></w:r></w:hyperlink>'
                % (rid, esc(label))
            )
        else:
            out.append('<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % esc(part))
    return ''.join(out)


def para(text, style=None, num=False, spacing=None):
    ppr = []
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if num:
        ppr.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
    if spacing:
        ppr.append(spacing)
    return '<w:p>%s%s</w:p>' % (
        '<w:pPr>%s</w:pPr>' % ''.join(ppr) if ppr else '',
        inline(text, CUR_RELS[0]),
    )


CUR_RELS = [None]


def build(blocks, path, doc_title, author):
    global CUR_RELS
    rels = []
    CUR_RELS = [rels]
    body = []
    for kind, text in blocks:
        if kind == 'name':
            body.append(para(text, 'ResumeName'))
        elif kind == 'tag':
            body.append(para(text, 'ResumeTag'))
        elif kind == 'meta':
            body.append(para(text, 'MetaLine'))
        elif kind == 'h2':
            body.append(para(text, 'SectionHeading'))
        elif kind == 'entry':
            body.append(para(text, 'EntryHeader'))
        elif kind == 'sub':
            body.append(para(text, 'SubEntry'))
        elif kind == 'bullet':
            body.append(para(text, 'Bullet', num=True))
        elif kind == 'body':
            body.append(para(text, 'BodyLine'))
        else:
            raise ValueError('unknown block kind: ' + kind)

    sectpr = (
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="720" w:right="1000" w:bottom="720" w:left="1000"'
        ' w:header="425" w:footer="425" w:gutter="0"/>'
        '<w:cols w:val="1" w:space="425"/><w:docGrid w:linePitch="312"/></w:sectPr>'
    )

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s%s</w:body></w:document>'
        % (W, R, ''.join(body), sectpr)
    )

    link_rels = ''.join(
        '<Relationship Id="%s" Type="%s/hyperlink" Target="%s" TargetMode="External"/>'
        % (rid, R, url) for rid, url in rels
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="%s/styles" Target="styles.xml"/>'
        '<Relationship Id="rId2" Type="%s/numbering" Target="numbering.xml"/>'
        '%s</Relationships>' % (R, R, link_rels)
    )

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                   '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
                   '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                   '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                   '</Types>')
        z.writestr('_rels/.rels',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="%s/officeDocument" Target="word/document.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                   '<Relationship Id="rId3" Type="%s/extended-properties" Target="docProps/app.xml"/>'
                   '</Relationships>' % (R, R))
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/document.xml', document)
        z.writestr('word/styles.xml', styles_xml())
        z.writestr('word/numbering.xml', numbering_xml())
        z.writestr('docProps/core.xml',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
                   ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"'
                   ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                   '<dc:title>%s</dc:title><dc:creator>%s</dc:creator>'
                   '<cp:lastModifiedBy>%s</cp:lastModifiedBy></cp:coreProperties>'
                   % (esc(doc_title), esc(author), esc(author)))
        z.writestr('docProps/app.xml',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Properties xmlns="%s/app" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
                   '<Application>Qoder docx-pro</Application><Company>%s</Company></Properties>'
                   % (R.replace('/relationships', '/extended-properties'), esc(author)))
    return path


FONT = ('<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Microsoft YaHei"/>')


def rpr(sz, bold=None, color=None, spacing=None, font=FONT):
    parts = ['<w:rPr>', font]
    if bold:
        parts.append('<w:b/>')
    if color:
        parts.append('<w:color w:val="%s"/>' % color)
    parts.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz))
    parts.append('</w:rPr>')
    return ''.join(parts)


def styles_xml():
    st = []
    st.append(
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="60" w:line="264" w:lineRule="auto"/></w:pPr>'
        + rpr(20) + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="ResumeName"><w:name w:val="Resume Name"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
        + rpr(34, bold=True) + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="ResumeTag"><w:name w:val="Resume Tag"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
        + rpr(22, bold=True, color='1F4E79') + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="MetaLine"><w:name w:val="Meta Line"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>'
        + rpr(18, color='595959') + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="SectionHeading"><w:name w:val="Section Heading"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:keepNext/><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="2" w:color="8EAADB"/></w:pBdr>'
        '<w:spacing w:before="180" w:after="70" w:line="240" w:lineRule="auto"/></w:pPr>'
        + rpr(23, bold=True, color='1F4E79') + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="EntryHeader"><w:name w:val="Entry Header"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:keepNext/><w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>'
        '<w:spacing w:before="100" w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
        % CONTENT_W + rpr(20, bold=True) + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="SubEntry"><w:name w:val="Sub Entry"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:keepNext/><w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>'
        + rpr(18, color='595959') + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="Bullet"><w:name w:val="Bullet"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="40" w:line="252" w:lineRule="auto"/>'
        '<w:ind w:left="227" w:hanging="227"/></w:pPr>'
        + rpr(19) + '</w:style>')
    st.append(
        '<w:style w:type="paragraph" w:styleId="BodyLine"><w:name w:val="Body Line"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="40" w:line="252" w:lineRule="auto"/></w:pPr>'
        + rpr(19) + '</w:style>')
    st.append(
        '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>'
        '<w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="%s"><w:docDefaults><w:rPrDefault>%s</w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="60" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults>%s</w:styles>' % (W, FONT + '<w:sz w:val="20"/><w:szCs w:val="20"/>', ''.join(st))
    )


def numbering_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:numbering xmlns:w="%s">'
        '<w:abstractNum w:abstractNumId="0">'
        '<w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
        '<w:lvlRestart w:val="0"/><w:lvlText w:val="&#8226;"/>'
        '<w:pPr><w:ind w:left="227" w:hanging="227"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:hint="default"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
        '<w:lvlRestart w:val="0"/><w:lvlText w:val="&#8211;"/>'
        '<w:pPr><w:ind w:left="454" w:hanging="227"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:hint="default"/></w:rPr></w:lvl>'
        '</w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        '</w:numbering>' % W
    )
