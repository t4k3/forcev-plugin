"""
Writer XLSX minimale, SENZA dipendenze (solo stdlib: zipfile + XML).
Un .xlsx e' uno ZIP di file XML. Stringhe inline (niente sharedStrings), due
stili (0=normale, 1=header grassetto). Sufficiente per report tabellari.

API:
    write_workbook(path, sheets)
    sheets = [ (sheet_name, headers:list[str], rows:list[list]) , ... ]
    Le celle: numeri -> numerici; tutto il resto -> testo.
"""
import zipfile
import html


def _colref(n: int) -> str:
    """1 -> A, 27 -> AA"""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref: str, val, style: int = 0) -> str:
    st = f' s="{style}"' if style else ""
    if isinstance(val, bool):
        val = str(val)
    if isinstance(val, (int, float)):
        return f'<c r="{ref}"{st}><v>{val}</v></c>'
    txt = html.escape("" if val is None else str(val))
    return f'<c r="{ref}"{st} t="inlineStr"><is><t xml:space="preserve">{txt}</t></is></c>'


def _sheet_xml(headers, rows) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    # header (riga 1, grassetto = stile 1)
    cells = "".join(_cell(f"{_colref(c+1)}1", h, 1) for c, h in enumerate(headers))
    out.append(f'<row r="1">{cells}</row>')
    # dati
    for r, row in enumerate(rows, start=2):
        cells = "".join(_cell(f"{_colref(c+1)}{r}", v, 0) for c, v in enumerate(row))
        out.append(f'<row r="{r}">{cells}</row>')
    out.append("</sheetData></worksheet>")
    return "".join(out)


STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
    '<cellXfs count="2"><xf/><xf fontId="1" applyFont="1"/></cellXfs>'
    '</styleSheet>'
)

CONTENT_TYPES_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
)

RELS_ROOT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)


def write_workbook(path, sheets):
    n = len(sheets)
    ct = [CONTENT_TYPES_HEAD]
    for i in range(1, n + 1):
        ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                  f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    ct.append("</Types>")

    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    for i, (name, _, _) in enumerate(sheets, start=1):
        wb.append(f'<sheet name="{html.escape(name)[:31]}" sheetId="{i}" r:id="rId{i}"/>')
    wb.append("</sheets></workbook>")

    wb_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i in range(1, n + 1):
        wb_rels.append(f'<Relationship Id="rId{i}" '
                       f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                       f'Target="worksheets/sheet{i}.xml"/>')
    wb_rels.append(f'<Relationship Id="rId{n+1}" '
                   f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                   f'Target="styles.xml"/>')
    wb_rels.append("</Relationships>")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", RELS_ROOT)
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(wb_rels))
        z.writestr("xl/styles.xml", STYLES)
        for i, (_, headers, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(headers, rows))
