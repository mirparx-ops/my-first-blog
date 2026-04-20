from .models import Pasto
from django.utils import timezone
from django.utils.timezone import localtime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from .forms import PastoForm
from collections import defaultdict
from xhtml2pdf import pisa
from io import BytesIO

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


# ─── Vista PDF ────────────────────────────────────────────────────────────────

def stampa_pdf(request):
    """
    Genera un PDF del diario in formato tabellare (una pagina per giorno).
    Ogni pagina riproduce il form cartaceo:
      colonne = pasti del giorno (max 5)
      righe   = ORA / LUOGO / CIBO / CON CHI / PRIMA / DOPO / SENSAZIONI

    GET ?data=YYYY-MM-DD  → solo quel giorno
    GET (nessuno)         → tutti i giorni registrati
    """
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        return HttpResponse(
            "WeasyPrint non è installato. Esegui: pip install weasyprint",
            status=500,
        )

    data_selezionata = request.GET.get('data')

    if data_selezionata:
        pasti_qs = Pasto.objects.filter(ora__date=data_selezionata).order_by('ora')
        titolo_periodo = data_selezionata
    else:
        pasti_qs = Pasto.objects.all().order_by('ora')
        titolo_periodo = None

    # ── Raggruppa per data locale, max 5 pasti per giorno ─────────────────
    MAX_COLONNE = 5

    giorni_dict = defaultdict(list)
    for pasto in pasti_qs:
        data_locale = localtime(pasto.ora).date()
        giorni_dict[data_locale].append(pasto)

    giorni = []
    for data_locale in sorted(giorni_dict.keys()):
        lista = giorni_dict[data_locale][:MAX_COLONNE]
        slot = lista + [None] * (MAX_COLONNE - len(lista))
        giorni.append({
            'data': data_locale,
            'slot': slot,
        })

    context = {
        'giorni': giorni,
        'titolo_periodo': titolo_periodo,
        'data_stampa': timezone.localdate(),
        'user': request.user,
    }

    html_string = render_to_string(
        'diario/diario_pdf.html', context, request=request
    )
    font_config = FontConfiguration()
    pdf_bytes = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(font_config=font_config)

    nome_file = f"diario_{data_selezionata or 'completo'}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nome_file}"'
    return response
