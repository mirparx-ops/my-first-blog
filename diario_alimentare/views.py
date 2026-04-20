from .models import Pasto
from django.utils import timezone
from django.utils.timezone import localtime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .forms import PastoForm
from collections import defaultdict


# ─── Viste esistenti ──────────────────────────────────────────────────────────

def diario_list(request):
    data_selezionata = request.GET.get('data')
    if data_selezionata:
        pasti = Pasto.objects.filter(ora__date=data_selezionata)
    else:
        pasti = Pasto.objects.all().order_by('-ora')
    return render(request, 'diario/diario_list.html', {'pasti': pasti})


def pasto_new(request):
    if request.method == "POST":
        form = PastoForm(request.POST)
        if form.is_valid():
            pasto = form.save(commit=False)
            pasto.save()
            return redirect('diario_list')
    else:
        form = PastoForm()
    return render(request, 'diario/pasto_edit.html', {'form': form})


def diario_detail(request, pk):
    pasto = get_object_or_404(Pasto, pk=pk)
    return render(request, 'diario/dettaglio_pasto.html', {'pasto': pasto})


# ─── Vista PDF con ReportLab ──────────────────────────────────────────────────

# Righe fisse del form cartaceo, nell'ordine corretto
MEAL_ROWS = ['Colazione', 'Spuntino', 'Pranzo', 'Merenda', 'Cena']


def _match_pasto(pasti_del_giorno, meal_name, already_used):
    """
    Trova il pasto che corrisponde al tipo di pasto richiesto.
    Per 'Spuntino' (che compare due volte), salta il primo già assegnato.
    Ritorna (pasto, idx) oppure (None, None).
    """
    for i, p in enumerate(pasti_del_giorno):
        if i in already_used:
            continue
        if p.title.strip().lower() == meal_name.lower():
            return p, i
    return None, None


def stampa_pdf(request):
    """
    Genera PDF del diario in formato tabellare con ReportLab.
    Layout: A4 landscape, una pagina per giorno.

    RIGHE  = Colazione / Spuntino / Pranzo / Spuntino / Cena  (fisse)
    COLONNE = ORA | LUOGO | COSA MANGIO | QUANTITÀ | CON CHI | PRIMA | DOPO | SENSAZIONI

    GET ?data=YYYY-MM-DD  → solo quel giorno
    GET (nessuno)         → tutti i giorni
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO

    # ── Dati ─────────────────────────────────────────────────────────────
    data_selezionata = request.GET.get('data')
    if data_selezionata:
        pasti_qs = Pasto.objects.filter(ora__date=data_selezionata).order_by('ora')
    else:
        pasti_qs = Pasto.objects.all().order_by('ora')

    giorni_dict = defaultdict(list)
    for p in pasti_qs:
        giorni_dict[localtime(p.ora).date()].append(p)

    giorni = [
        {'data': d, 'pasti': giorni_dict[d]}
        for d in sorted(giorni_dict.keys())
    ]

    # ── Documento ─────────────────────────────────────────────────────────
    buffer = BytesIO()
    PAGE   = landscape(A4)
    W, H   = PAGE
    MARGIN = 12 * mm

    doc = SimpleDocTemplate(
        buffer, pagesize=PAGE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=10 * mm, bottomMargin=10 * mm,
    )

    # ── Colori ────────────────────────────────────────────────────────────
    COL_HEADER_BG  = colors.HexColor('#f0ece4')   # sfondo intestazioni colonne
    ROW_LABEL_BG   = colors.HexColor('#f5f2ee')   # sfondo etichette pasto
    GRID_COLOR     = colors.HexColor('#aaaaaa')
    BORDER_COLOR   = colors.HexColor('#555555')
    TEXT_DARK      = colors.HexColor('#222222')
    TEXT_LABEL     = colors.HexColor('#4a3728')

    # ── Stili testo ───────────────────────────────────────────────────────
    s_col_header = ParagraphStyle(
        'col_h', fontSize=6.5, fontName='Helvetica-Bold',
        alignment=TA_CENTER, leading=8, textColor=TEXT_LABEL,
    )
    s_row_label = ParagraphStyle(
        'row_l', fontSize=8.5, fontName='Helvetica-Bold',
        alignment=TA_CENTER, leading=10, textColor=TEXT_LABEL,
    )
    s_cell = ParagraphStyle(
        'cell', fontSize=8, fontName='Helvetica',
        alignment=TA_LEFT, leading=10, textColor=TEXT_DARK,
    )
    s_brand = ParagraphStyle(
        'brand', fontSize=10, fontName='Helvetica-BoldOblique', leading=12,
    )
    s_date = ParagraphStyle(
        'date', fontSize=11, fontName='Helvetica-Bold',
        leading=13, alignment=TA_CENTER,
    )

    def P(text, style):
        return Paragraph(str(text) if text else '', style)

    def cell(text):
        return P(text, s_cell)

    # ── Larghezze colonne ─────────────────────────────────────────────────
    usable = W - 2 * MARGIN

    # [etichetta pasto | ORA | LUOGO | COSA MANGIO | CON CHI | PRIMA | DOPO | SENSAZIONI]
    col_w = [
        20 * mm,   # etichetta pasto (riga)
        14 * mm,   # ORA
        24 * mm,   # LUOGO
        44 * mm,   # COSA MANGIO E COSA BEVO (allargata)
        22 * mm,   # CON CHI
        # le ultime 3 dividono lo spazio rimanente
    ]
    remaining = usable - sum(col_w)
    emotional_w = remaining / 3
    col_w += [emotional_w, emotional_w, emotional_w]

    # ── Altezze righe ─────────────────────────────────────────────────────
    HEADER_H = 10 * mm
    ROW_H    = 28 * mm

    # ── Intestazioni colonne ──────────────────────────────────────────────
    COL_HEADERS = [
        '',
        'ORA',
        'LUOGO',
        'COSA\nMANGIO\nE COSA\nBEVO',
        'CON\nCHI',
        'COME MI SENTO\nPRIMA DEL PASTO\nE PERCHÉ',
        'COME MI SENTO\nDOPO IL PASTO\nE PERCHÉ',
        'SENSAZIONI\nFISICHE\no Cambiamenti',
    ]

    # ── Costruzione storia ────────────────────────────────────────────────
    story = []
    nome_utente = request.user.get_full_name() or request.user.username

    for idx, giorno in enumerate(giorni):
        pasti_giorno = giorno['pasti']

        # Abbina ogni riga fissa al pasto corrispondente per titolo
        already_used = set()
        righe_pasto = []
        for meal_name in MEAL_ROWS:
            p, i = _match_pasto(pasti_giorno, meal_name, already_used)
            if i is not None:
                already_used.add(i)
            righe_pasto.append(p)   # p può essere None se non registrato

        # ── Header pagina ─────────────────────────────────────────────
        hdr_data = [[
            P(f'<i>Diario Alimentare di</i>  <b>{nome_utente}</b>', s_brand),
            P(f'DATA &nbsp;&nbsp; <b>{giorno["data"].strftime("%d / %m / %Y")}</b>', s_date),
        ]]
        hdr_t = Table(hdr_data, colWidths=[usable * 0.6, usable * 0.4])
        hdr_t.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(hdr_t)
        story.append(Spacer(1, 3 * mm))

        # ── Tabella ───────────────────────────────────────────────────
        # Prima riga: intestazioni colonne
        table_data = [[P(h, s_col_header) for h in COL_HEADERS]]

        # Una riga per ogni tipo di pasto
        for meal_name, p in zip(MEAL_ROWS, righe_pasto):
            ora_str   = localtime(p.ora).strftime('%H:%M') if p else ''
            luogo_str = p.luogo             if p else ''
            cibo_str  = p.cibo              if p else ''
            chi_str   = p.conChi            if p else ''
            prima_str = p.come_sento_prima  if p else ''
            dopo_str  = p.come_sento_dopo   if p else ''
            sens_str  = p.sensazione        if p else ''

            row = [
                P(meal_name, s_row_label),
                cell(ora_str),
                cell(luogo_str),
                cell(cibo_str),
                cell(chi_str),
                cell(prima_str),
                cell(dopo_str),
                cell(sens_str),
            ]
            table_data.append(row)

        row_heights = [HEADER_H] + [ROW_H] * len(MEAL_ROWS)

        t = Table(table_data, colWidths=col_w, rowHeights=row_heights)
        t.setStyle(TableStyle([
            # Bordi
            ('BOX',          (0, 0), (-1, -1), 1.2, BORDER_COLOR),
            ('INNERGRID',    (0, 0), (-1, -1), 0.5, GRID_COLOR),

            # Intestazione colonne (riga 0)
            ('BACKGROUND',   (0, 0), (-1, 0),  COL_HEADER_BG),
            ('VALIGN',       (0, 0), (-1, 0),  'MIDDLE'),
            ('LINEBELOW',    (0, 0), (-1, 0),  1.2, BORDER_COLOR),

            # Colonna etichette pasto (colonna 0, righe dati)
            ('BACKGROUND',   (0, 1), (0, -1),  ROW_LABEL_BG),
            ('VALIGN',       (0, 1), (0, -1),  'MIDDLE'),
            ('LINEAFTER',    (0, 0), (0, -1),  1.2, BORDER_COLOR),

            # Celle dati
            ('VALIGN',       (1, 1), (-1, -1), 'TOP'),
            ('TOPPADDING',   (1, 1), (-1, -1), 4),
            ('LEFTPADDING',  (1, 1), (-1, -1), 4),
            ('RIGHTPADDING', (1, 1), (-1, -1), 3),

            # Separatore più netto prima delle colonne emotive
            ('LINEBEFORE',   (6, 0), (6, -1),  1.0, BORDER_COLOR),
        ]))

        story.append(t)

        if idx < len(giorni) - 1:
            story.append(PageBreak())

    if not story:
        story.append(P('Nessun pasto registrato.', s_cell))

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    nome_file = f"diario_{data_selezionata or 'completo'}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nome_file}"'
    return response
