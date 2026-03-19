from django.shortcuts import render
from .models import Post
from django.utils import timezone
from django.shortcuts import render,get_object_or_404, redirect
from .forms import PostForm

def post_list(request):
    posts = Post.objects.filter(published_date__lte=timezone.now()).order_by('published_date')
    # posts = Post.objects.all().order_by('-published_date')
    return render(request, 'blog/post_list.html', {'posts':posts})


def post_list_2(request):
    return render(request, 'blog/post_list_2.html', {})

def post_details(request,pk):
    post= get_object_or_404(Post, pk=pk)
    return render(request, 'blog/post_details.html', {'post':post})

def post_new(request):
    
    if request.method =="POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save( commit = False )
            post.author =  request.user
            post.published_date = timezone.now()
            post.save()
            #return redirect('post_details', pk=post.pk)
            return redirect('post_list')
    else:       
        form = PostForm()
    return render(request,'blog/post_edit.html', {'form': form})

def post_edit(request,pk):
    post =get_object_or_404(Post, pk=pk)
    if request.method =="POST":
        form =  PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author=request.user
            post.plublished_date = timezone.now()
            post.save()
            #return redirect('post_details',pk=post.pk)
            return redirect('post_list')
    else:
        form = PostForm(instance=post)
    return render(request,'blog/post_edit.html',{'form' : form})

# Create your views here.
