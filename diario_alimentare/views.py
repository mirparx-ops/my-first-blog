from .models import Pasto
from django.utils import timezone
from django.shortcuts import render,get_object_or_404, redirect

def diario_list(request):
    data_selezionata = request.GET.get('data')

    if data_selezionata:
        pasti = Pasto.objects.filter(ora__date=data_selezionata)
    else:
        pasti = Pasto.objects.all().order_by('-ora')
    # posts = Post.objects.all().order_by('-published_date')
    return render(request, 'diario/diario_list.html', {'pasti':pasti})


def diario_detail(request, pk):
    pasti=get_object_or_404(Pasto, pk=pk)
    return render(request,'diario/dettaglio_pasto.hmtl', {'pasti':pasti})