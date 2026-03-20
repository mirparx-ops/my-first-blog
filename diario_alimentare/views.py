from django.shortcuts import render
from .models import Pasto
from django.utils import timezone


def diario_list(request):
    data_selezionata = request.GET.get('data')

    if data_selezionata:
        pasti = Pasto.objects.filter(ora__date=data_selezionata)
    else:
        pasti = Pasto.objects.all().order_by('-ora')
    # posts = Post.objects.all().order_by('-published_date')
    return render(request, 'diario/diario_list.html', {'pasti':pasti})
