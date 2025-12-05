# functions/pdf_exporters.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# Tenta registrar DejaVuSans para acentuação; cai para Helvetica se não existir
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
    DEFAULT_FONT = "DejaVuSans"
except Exception:
    DEFAULT_FONT = "Helvetica"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 20 * mm

def _replace_placeholders(text: str, ata: dict, detalhes: dict):
    if not text:
        return ""
    res = str(text)
    # placeholders simples
    nome = ata.get("ala_nome") or ata.get("ala") or ""
    data = ata.get("data") or ""
    tema = (detalhes or {}).get("tema") or ""
    res = res.replace("[NOME]", nome)
    res = res.replace("[DATA]", data)
    res = res.replace("[TEMA]", tema)
    return res

def _wrap_text_lines(text, font_name, font_size, max_width):
    if not text:
        return []
    words = text.replace("\r", "").split()
    lines = []
    line = ""
    for w in words:
        candidate = w if line == "" else f"{line} {w}"
        width = pdfmetrics.stringWidth(candidate, font_name, font_size)
        if width <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def _draw_wrapped(c, text, x, y, width, font_name=DEFAULT_FONT, font_size=10, leading=None):
    if leading is None:
        leading = font_size * 1.2
    c.setFont(font_name, font_size)
    paragraphs = str(text).split("\n")
    for p in paragraphs:
        p = p.strip()
        if p == "":
            y -= leading
        else:
            lines = _wrap_text_lines(p, font_name, font_size, width)
            for ln in lines:
                c.drawString(x, y, ln)
                y -= leading
                if y < MARGIN:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = PAGE_HEIGHT - MARGIN
    return y

def _section_title(c, text, x, y, font_name=DEFAULT_FONT, size=12):
    c.setFillColor(colors.HexColor("#0b4b71"))
    c.setFont(font_name, size)
    c.drawString(x, y, text)
    y -= size * 1.2
    c.setFillColor(colors.black)
    return y

def _create_pdf_from_ata(ata: dict, detalhes: dict, template: dict=None):
    if detalhes is None:
        detalhes = {}
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    x = MARGIN
    y = PAGE_HEIGHT - MARGIN

    # Header
    c.setFont(DEFAULT_FONT, 16)
    title = f"Ata {str(ata.get('tipo') or '').capitalize()} - {ata.get('data') or ''}"
    c.drawString(x, y, title)
    y -= 18

    # Status
    status = ata.get('status') or "Completa"
    c.setFont(DEFAULT_FONT, 10)
    c.setFillColor(colors.HexColor("#2f855a"))
    c.drawString(x, y, f"Status: {status}")
    c.setFillColor(colors.black)
    y -= 14

    # BOAS VINDAS (padrão; template.boas_vindas)
    y = _section_title(c, "BOAS VINDAS", x, y)
    if template and template.get('boas_vindas'):
        boas = _replace_placeholders(template.get('boas_vindas'), ata, detalhes)
        y = _draw_wrapped(c, boas, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6
    # Tema dinâmico (se existir)
    tema = detalhes.get('tema')
    if tema:
        y = _draw_wrapped(c, f"TEMA: {tema}", x, y, PAGE_WIDTH - 2*MARGIN, font_size=11)
        y -= 8

    # ABERTURA (não insere mensagens automáticas; apenas campos preenchidos)
    y = _section_title(c, "ABERTURA", x, y)
    if detalhes.get('reconhecemos_presenca'):
        y = _draw_wrapped(c, f"Reconhecemos a presença: {detalhes.get('reconhecemos_presenca')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 4
    if detalhes.get('anuncios'):
        anuncios = detalhes.get('anuncios')
        anuncios_text = "\n".join(anuncios) if isinstance(anuncios, (list,tuple)) else str(anuncios)
        y = _draw_wrapped(c, f"Anúncios:\n{anuncios_text}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 4
    if detalhes.get('hino_abertura'):
        y = _draw_wrapped(c, f"Hino de Abertura: {detalhes.get('hino_abertura')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 4
    if detalhes.get('oracao_abertura'):
        y = _draw_wrapped(c, f"Oração de Abertura: {detalhes.get('oracao_abertura')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6

    # AÇÕES — usar exatamente as chaves do DB conforme solicitado
    y = _section_title(c, "AÇÕES", x, y)
    action_fields = [
        ("desobrigacoes", "Desobrigações"),
        ("apoios", "Apoios"),
        ("confirmacoes_batismo", "Confirmações Batismais"),
        ("apoio_membro_novo", "Apoio a Novos Membros"),
        ("bencao_crianca", "Bênção de Crianças"),
    ]

    for key, label in action_fields:
        # 1) mostrar mensagem pré-configurada do template (se houver)
        if template and template.get(key):
            msg = _replace_placeholders(template.get(key), ata, detalhes)
            # mostramos a orientação do template em itálico visual (aqui apenas como texto separado)
            y = _draw_wrapped(c, msg, x, y, PAGE_WIDTH - 2*MARGIN, font_size=10)
            y -= 3
        # 2) mostrar conteúdo real de detalhes (se existir)
        val = detalhes.get(key)
        if val:
            val_text = "\n".join(val) if isinstance(val, (list,tuple)) else str(val)
            y = _draw_wrapped(c, f"{label}:\n{val_text}", x, y, PAGE_WIDTH - 2*MARGIN)
            y -= 6

    # SACRAMENTO (padrão)
    y = _section_title(c, "SACRAMENTO", x, y)
    if template and template.get('sacramento'):
        sac = _replace_placeholders(template.get('sacramento'), ata, detalhes)
        y = _draw_wrapped(c, sac, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6
    if detalhes.get('hino_sacramental'):
        y = _draw_wrapped(c, f"Hino Sacramental: {detalhes.get('hino_sacramental')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6

    # MENSAGENS
    y = _section_title(c, "MENSAGENS", x, y)
    if template and template.get('mensagens'):
        y = _draw_wrapped(c, _replace_placeholders(template.get('mensagens'), ata, detalhes), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6
    # Discursantes: 2 padrão; se mais, iterativo
    discursantes = detalhes.get('discursantes') or []
    if isinstance(discursantes, (list,tuple)) and discursantes:
        texto = "\n".join([f"{i+1}º - {d}" for i,d in enumerate(discursantes)])
        y = _draw_wrapped(c, "Discursantes:\n" + texto, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6
    if detalhes.get('hino_intermediario'):
        y = _draw_wrapped(c, f"Hino Intermediário: {detalhes.get('hino_intermediario')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6

    # AGRADECIMENTOS FINAIS (padrão) e ENCERRAMENTO (padrão)
    y = _section_title(c, "AGRADECIMENTOS FINAIS", x, y)
    if template and template.get('encerramento'):
        y = _draw_wrapped(c, _replace_placeholders(template.get('encerramento'), ata, detalhes), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6

    y = _section_title(c, "ENCERRAMENTO", x, y)
    if template and template.get('encerramento'):
        y = _draw_wrapped(c, _replace_placeholders(template.get('encerramento'), ata, detalhes), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6
    if detalhes.get('hino_encerramento'):
        y = _draw_wrapped(c, f"Hino de Encerramento: {detalhes.get('hino_encerramento')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 4
    if detalhes.get('oracao_encerramento'):
        y = _draw_wrapped(c, f"Oração de Encerramento: {detalhes.get('oracao_encerramento')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 6

    # Footer
    c.setFont(DEFAULT_FONT, 8)
    c.setFillColor(colors.HexColor("#6b7280"))
    c.drawRightString(PAGE_WIDTH - MARGIN, MARGIN / 2, "Gerado pelo Sistema de Atas")
    c.showPage()
    c.save()
    out.seek(0)
    return out

# API pública
def exportar_pdf_bytes(ata, detalhes=None, template=None, filename="ata.pdf"):
    """
    Gera PDF e retorna (BytesIO_buffer, filename, mimetype).
    - `ata`: dict com dados da ata
    - `detalhes`: dict com detalhes específicos
    - `template`: dict com mensagens padrão (campos conforme a tabela templates)
    """
    if not isinstance(ata, dict):
        # compat: se vier HTML/string, gera PDF simples com o texto
        html_string = str(ata or "")
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont(DEFAULT_FONT, 10)
        y = PAGE_HEIGHT - MARGIN
        for ln in html_string.splitlines():
            c.drawString(MARGIN, y, ln[:200])
            y -= 12
            if y < MARGIN:
                c.showPage()
                c.setFont(DEFAULT_FONT, 10)
                y = PAGE_HEIGHT - MARGIN
        c.save()
        buf.seek(0)
        return buf, filename, "application/pdf"

    buffer = _create_pdf_from_ata(ata, detalhes or {}, template)
    buffer.seek(0)
    return buffer, filename, "application/pdf"

def exportar_sacramental_bytes(ata, detalhes=None, template=None, filename="ata_sacramental.pdf"):
    return exportar_pdf_bytes(ata, detalhes=detalhes, template=template, filename=filename)