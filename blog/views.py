from django.shortcuts import render


def post_list(request):
    return render(request, 'blog/post_list.html', {})

def post_list_2(request):
    return render(request, 'blog/post_list_2.html', {})

# Create your views here.
