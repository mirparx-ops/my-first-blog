from django.shortcuts import render
from .models import Pasto
from django.utils import timezone


def diario_list(request):
    pasti = Pasto.objects.all()
    # posts = Post.objects.all().order_by('-published_date')
    return render(request, 'diario/diario_list.html', {'pasti':pasti})

