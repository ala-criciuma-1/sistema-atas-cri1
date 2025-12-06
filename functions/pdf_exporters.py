# functions/pdf_exporters.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Tenta registrar DejaVuSans para acentuação; cai para Helvetica se não existir
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
    DEFAULT_FONT = "DejaVuSans"
except Exception:
    DEFAULT_FONT = "Helvetica"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm

ACCENT_COLOR = colors.HexColor("#0b4b71")
SECONDARY_COLOR = colors.HexColor("#2f855a")
LIGHT_GRAY = colors.HexColor("#f8f9fa")
DARK_TEXT = colors.HexColor("#1a202c")

def _replace_placeholders(text: str, ata: dict, detalhes: dict):
    if not text:
        return ""
    res = str(text)
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

# Changed default font_size from 10 to 12
def _draw_wrapped(c, text, x, y, width, font_name=DEFAULT_FONT, font_size=12, leading=None, color=DARK_TEXT):
    if leading is None:
        leading = font_size * 1.2
    c.setFont(font_name, font_size)
    c.setFillColor(color)
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
                    c.setFillColor(color)
                    y = PAGE_HEIGHT - MARGIN
    c.setFillColor(DARK_TEXT)
    return y

# Increased size from 13 to 16, increased vertical space from y -= 12 to y -= 20
def _section_title(c, text, x, y, font_name=DEFAULT_FONT, size=16):
    # Modern section header with background
    c.setFillColor(ACCENT_COLOR)
    c.setFont(font_name, size)
    c.drawString(x, y, text)
    y -= 2
    # Underline
    c.setLineWidth(2)
    c.line(x, y - 2, x + pdfmetrics.stringWidth(text, font_name, size), y - 2)
    y -= 20 # Increased space
    c.setFillColor(DARK_TEXT)
    return y

# Increased size from 11 to 13
def _section_label(c, text, x, y, font_name=DEFAULT_FONT, size=13):
    c.setFont(font_name, size)
    c.setFillColor(ACCENT_COLOR)
    c.drawString(x, y, text)
    c.setFillColor(DARK_TEXT)
    return y - (size * 1.3)

def _create_pdf_from_ata(ata: dict, detalhes: dict, template: dict=None):
    if detalhes is None:
        detalhes = {}
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    x = MARGIN
    y = PAGE_HEIGHT - MARGIN

    # ===== HEADER =====
    c.setFont(DEFAULT_FONT, 20) # Increased size from 18 to 20
    c.setFillColor(ACCENT_COLOR)
    title = f"Ata {str(ata.get('tipo') or '').capitalize()}"
    c.drawString(x, y, title)
    y -= 24 # Increased vertical shift

    # Date
    c.setFont(DEFAULT_FONT, 13) # Increased size from 11 to 13
    c.setFillColor(colors.gray)
    data_str = ata.get('data') or ''
    c.drawString(x, y, f"Data: {data_str}")
    y -= 18 # Increased vertical shift

    # # Status badge - REMOVED AS REQUESTED
    # status = ata.get('status') or "Completa"
    # c.setFillColor(SECONDARY_COLOR)
    # c.rect(x, y - 12, 80, 12, fill=True)
    # c.setFont(DEFAULT_FONT, 9)
    # c.setFillColor(colors.white)
    # c.drawString(x + 4, y - 10, f"Status: {status}")
    # c.setFillColor(DARK_TEXT)
    # y -= 28
    
    y -= 4 # Adjusting y position after removing the badge

    # ===== TEMA (if exists) =====
    tema = detalhes.get('tema')
    if tema:
        c.setFont(DEFAULT_FONT, 15) # Increased size from 12 to 15
        c.setFillColor(ACCENT_COLOR)
        c.drawString(x, y, "TEMA DA REUNIÃO")
        y -= 16 # Increased vertical shift
        c.setFont(DEFAULT_FONT, 12) # Increased size from 10 to 12
        c.setFillColor(DARK_TEXT)
        # _draw_wrapped now defaults to 12, so no need for font_size=10
        y = _draw_wrapped(c, tema, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== BOAS VINDAS =====
    y = _section_title(c, "BOAS VINDAS", x, y)
    if template and template.get('boas_vindas'):
        boas = _replace_placeholders(template.get('boas_vindas'), ata, detalhes)
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, boas, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== ABERTURA =====
    y = _section_title(c, "ABERTURA", x, y)
    abertura_data = []
    if detalhes.get('presidido'):
        abertura_data.append(f"Presidido por: {detalhes.get('presidido')}")
    if detalhes.get('dirigido'):
        abertura_data.append(f"Dirigido por: {detalhes.get('dirigido')}")
    if detalhes.get('recepcionistas'):
        abertura_data.append(f"Recepcionistas: {detalhes.get('recepcionistas')}")
    if detalhes.get('reconhecemos_presenca'):
        abertura_data.append(f"Reconhecemos: {detalhes.get('reconhecemos_presenca')}")
    if detalhes.get('hino_abertura'):
        abertura_data.append(f"Hino: {detalhes.get('hino_abertura')}")
    if detalhes.get('oracao_abertura'):
        abertura_data.append(f"Oração: {detalhes.get('oracao_abertura')}")
    
    if abertura_data:
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, "\n".join(abertura_data), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    if detalhes.get('anuncios'):
        y -= 4
        anuncios = detalhes.get('anuncios')
        anuncios_text = "\n".join(anuncios) if isinstance(anuncios, (list,tuple)) else str(anuncios)
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, f"📢 Anúncios:\n{anuncios_text}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== AÇÕES =====
    action_fields = [
        ("desobrigacoes", "Desobrigações"),
        ("apoios", "Apoios"),
        ("confirmacoes_batismo", "Confirmações Batismais"),
        ("apoio_membro_novo", "Apoio a Novos Membros"),
        ("bencao_crianca", "Bênção de Crianças"),
    ]
    
    has_actions = any(detalhes.get(key) for key, _ in action_fields)
    if has_actions:
        y = _section_title(c, "AÇÕES", x, y)
        for key, label in action_fields:
            val = detalhes.get(key)
            if val:
                val_text = "\n".join(val) if isinstance(val, (list,tuple)) else str(val)
                # Removed font_size=10 to use new default of 12
                y = _draw_wrapped(c, f"• {label}: {val_text}", x, y, PAGE_WIDTH - 2*MARGIN)
                y -= 8 # Increased vertical shift
        y -= 6 # Increased vertical shift

    # ===== SACRAMENTO =====
    y = _section_title(c, "SACRAMENTO", x, y)
    sacramento_data = []
    if template and template.get('sacramento'):
        sac = _replace_placeholders(template.get('sacramento'), ata, detalhes)
        sacramento_data.append(sac)
    if detalhes.get('hino_sacramental'):
        sacramento_data.append(f"Hino: {detalhes.get('hino_sacramental')}")
    
    if sacramento_data:
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, "\n".join(sacramento_data), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== MENSAGENS / DISCURSANTES =====
    y = _section_title(c, "MENSAGENS", x, y)
    if template and template.get('mensagens'):
        msg_text = _replace_placeholders(template.get('mensagens'), ata, detalhes)
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, msg_text, x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 8 # Increased vertical shift

    discursantes = detalhes.get('discursantes') or []
    if isinstance(discursantes, (list,tuple)) and discursantes:
        disc_list = "\n".join([f"  {i+1}º - {d}" for i,d in enumerate(discursantes)])
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, f"Discursantes:\n{disc_list}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 10 # Increased vertical shift

    if detalhes.get('ultimo_discursante'):
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, f"  3º/Último - {detalhes.get('ultimo_discursante')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 10 # Increased vertical shift

    if detalhes.get('hino_intermediario'):
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, f"Hino Intermediário: {detalhes.get('hino_intermediario')}", x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== AGRADECIMENTOS / ENCERRAMENTO =====
    y = _section_title(c, "ENCERRAMENTO", x, y)
    encerramento_data = []
    if template and template.get('encerramento'):
        enc = _replace_placeholders(template.get('encerramento'), ata, detalhes)
        encerramento_data.append(enc)
    if detalhes.get('hino_encerramento'):
        encerramento_data.append(f"Hino: {detalhes.get('hino_encerramento')}")
    if detalhes.get('oracao_encerramento'):
        encerramento_data.append(f"Oração: {detalhes.get('oracao_encerramento')}")
    
    if encerramento_data:
        # Removed font_size=10 to use new default of 12
        y = _draw_wrapped(c, "\n".join(encerramento_data), x, y, PAGE_WIDTH - 2*MARGIN)
        y -= 12 # Increased vertical shift

    # ===== FOOTER =====
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.line(MARGIN, MARGIN + 10, PAGE_WIDTH - MARGIN, MARGIN + 10)
    
    c.setFont(DEFAULT_FONT, 10) # Increased size from 8 to 10
    c.setFillColor(colors.HexColor("#718096"))
    c.drawString(MARGIN, MARGIN + 2, "Sistema de Atas - Ala Criciúma")
    c.drawRightString(PAGE_WIDTH - MARGIN, MARGIN + 2, f"Página 1")
    
    c.showPage()
    c.save()
    out.seek(0)
    return out

# API pública
def exportar_pdf_bytes(ata, detalhes=None, template=None, filename="ata.pdf"):
    """
    Gera PDF e retorna (BytesIO_buffer, filename, mimetype).
    """
    if not isinstance(ata, dict):
        html_string = str(ata or "")
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont(DEFAULT_FONT, 12) # Increased size from 10 to 12
        y = PAGE_HEIGHT - MARGIN
        for ln in html_string.splitlines():
            c.drawString(MARGIN, y, ln[:200])
            y -= 14 # Increased vertical shift
            if y < MARGIN:
                c.showPage()
                c.setFont(DEFAULT_FONT, 12) # Increased size from 10 to 12
                y = PAGE_HEIGHT - MARGIN
        c.save()
        buf.seek(0)
        return buf, filename, "application/pdf"

    buffer = _create_pdf_from_ata(ata, detalhes or {}, template)
    buffer.seek(0)
    return buffer, filename, "application/pdf"

def exportar_sacramental_bytes(ata, detalhes=None, template=None, filename="ata_sacramental.pdf"):
    return exportar_pdf_bytes(ata, detalhes=detalhes, template=template, filename=filename)