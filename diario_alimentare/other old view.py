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

def stampa_pdf(request):
    """
    Genera un PDF del diario in formato tabellare con ReportLab.
    Layout: A4 landscape, una pagina per giorno.
    Colonne = pasti (max 5), Righe = campi del diario.

    GET ?data=YYYY-MM-DD  → solo quel giorno
    GET (nessuno)         → tutti i giorni
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO

    # ── Raccolta dati ─────────────────────────────────────────────────────
    data_selezionata = request.GET.get('data')
    if data_selezionata:
        pasti_qs = Pasto.objects.filter(ora__date=data_selezionata).order_by('ora')
    else:
        pasti_qs = Pasto.objects.all().order_by('ora')

    MAX_COLONNE = 5
    giorni_dict = defaultdict(list)
    for pasto in pasti_qs:
        data_locale = localtime(pasto.ora).date()
        giorni_dict[data_locale].append(pasto)

    giorni = []
    for data_locale in sorted(giorni_dict.keys()):
        lista = giorni_dict[data_locale][:MAX_COLONNE]
        slot = lista + [None] * (MAX_COLONNE - len(lista))
        giorni.append({'data': data_locale, 'slot': slot})

    # ── Setup documento ───────────────────────────────────────────────────
    buffer = BytesIO()
    PAGE = landscape(A4)
    W, H = PAGE

    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    # ── Stili paragrafo ───────────────────────────────────────────────────
    SEPIA      = colors.HexColor('#6b5444')
    LIGHT_GREY = colors.HexColor('#f5f5f5')
    MID_GREY   = colors.HexColor('#888888')
    BORDER     = colors.HexColor('#999999')

    style_header = ParagraphStyle(
        'header', fontSize=9, leading=11,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
    )
    style_label = ParagraphStyle(
        'label', fontSize=7, leading=9,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
        textColor=colors.HexColor('#333333'),
    )
    style_cell = ParagraphStyle(
        'cell', fontSize=8, leading=10,
        fontName='Helvetica', alignment=TA_LEFT,
    )
    style_brand = ParagraphStyle(
        'brand', fontSize=10, leading=12,
        fontName='Helvetica-BoldOblique',
    )
    style_date = ParagraphStyle(
        'date', fontSize=10, leading=12,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
    )

    # ── Funzione helper: testo di cella ───────────────────────────────────
    def cell(text):
        return Paragraph(str(text) if text else '', style_cell)

    def label(text):
        return Paragraph(text, style_label)

    # ── Dimensioni colonne ────────────────────────────────────────────────
    usable_w = W - 24 * mm           # larghezza utile
    label_w  = 20 * mm               # colonna etichetta
    pasto_w  = (usable_w - label_w) / MAX_COLONNE

    col_widths = [label_w] + [pasto_w] * MAX_COLONNE

    # Altezze righe (mm → punti: 1mm ≈ 2.835pt)
    ROW_HEIGHTS = [
        8  * mm,   # intestazione pasto
        8  * mm,   # ORA
        8  * mm,   # LUOGO
        20 * mm,   # COSA MANGIO
        14 * mm,   # QUANTITÀ
        8  * mm,   # CON CHI
        22 * mm,   # PRIMA
        22 * mm,   # DOPO
        14 * mm,   # SENSAZIONI
    ]

    # Definizione righe: (label, field_extractor)
    RIGHE = [
        ('ORA',
         lambda p: cell(localtime(p.ora).strftime('%H:%M') if p else '')),
        ('LUOGO',
         lambda p: cell(p.luogo if p else '')),
        ('COSA\nMANGIO\nE COSA\nBEVO',
         lambda p: cell(p.cibo if p else '')),
        ('QUANTITÀ\n(PORZIONE\nO GRAMMI)',
         lambda p: cell('')),           # campo non nel modello → spazio libero
        ('CON CHI',
         lambda p: cell(p.conChi if p else '')),
        ('COME MI\nSENTO\nPRIMA DEL\nPASTO E\nPERCHÉ',
         lambda p: cell(p.come_sento_prima if p else '')),
        ('COME MI\nSENTO\nDOPO IL\nPASTO E\nPERCHÉ',
         lambda p: cell(p.come_sento_dopo if p else '')),
        ('SENSAZIONI\nFISICHE o\nCambiamenti',
         lambda p: cell(p.sensazione if p else '')),
    ]

    # ── Costruzione storia PDF ─────────────────────────────────────────────
    story = []

    if not giorni:
        story.append(Paragraph('Nessun pasto registrato.', style_cell))
    
    nome_utente = request.user.get_full_name() or request.user.username

    for idx, giorno in enumerate(giorni):
        slot = giorno['slot']

        # ── Header pagina ─────────────────────────────────────────────
        header_data = [[
            Paragraph(f'<i>Diario Alimentare di</i> <b>{nome_utente}</b>', style_brand),
            Paragraph(
                f'DATA &nbsp; <b>{giorno["data"].strftime("%d / %m / %Y")}</b>',
                style_date
            ),
        ]]
        header_table = Table(header_data, colWidths=[usable_w * 0.6, usable_w * 0.4])
        header_table.setStyle(TableStyle([
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 3 * mm))

        # ── Intestazione colonne ──────────────────────────────────────
        col_header_row = [label('')]
        for pasto in slot:
            testo = pasto.title if pasto else ''
            col_header_row.append(Paragraph(testo, style_header))

        # ── Righe dati ────────────────────────────────────────────────
        table_data = [col_header_row]
        for riga_label, extractor in RIGHE:
            row = [label(riga_label)]
            for pasto in slot:
                row.append(extractor(pasto))
            table_data.append(row)

        # ── Stile tabella ─────────────────────────────────────────────
        ts = TableStyle([
            # Bordi generali
            ('GRID',        (0, 0), (-1, -1), 0.5, BORDER),
            ('BOX',         (0, 0), (-1, -1), 1.0, colors.HexColor('#555555')),

            # Intestazione colonne pasto
            ('BACKGROUND',  (1, 0), (-1, 0), LIGHT_GREY),
            ('FONTNAME',    (1, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (1, 0), (-1, 0), 8),
            ('ALIGN',       (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN',      (0, 0), (-1, 0), 'MIDDLE'),

            # Colonna etichette
            ('BACKGROUND',  (0, 0), (0, -1), LIGHT_GREY),
            ('ALIGN',       (0, 0), (0, -1), 'CENTER'),
            ('VALIGN',      (0, 0), (0, -1), 'MIDDLE'),

            # Celle dati
            ('VALIGN',      (1, 1), (-1, -1), 'TOP'),
            ('FONTNAME',    (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',    (1, 1), (-1, -1), 8),
            ('TOPPADDING',  (1, 1), (-1, -1), 3),
            ('LEFTPADDING', (1, 1), (-1, -1), 4),

            # Bordo sinistro più spesso per separare le etichette
            ('LINEAFTER',   (0, 0), (0, -1), 1.5, colors.HexColor('#555555')),
        ])

        t = Table(table_data, colWidths=col_widths, rowHeights=ROW_HEIGHTS)
        t.setStyle(ts)
        story.append(t)

        # Nuova pagina tra i giorni (tranne l'ultimo)
        if idx < len(giorni) - 1:
            story.append(PageBreak())

    # ── Build e risposta ──────────────────────────────────────────────────
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    nome_file = f"diario_{data_selezionata or 'completo'}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nome_file}"'
    return response
