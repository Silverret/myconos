import os

from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from .forms import ImageUploadForm

from api.main import main as api_main

# Create your views here.
def index(request):
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']

        dir_path = os.path.join(settings.MEDIA_ROOT, 'input')
        fs = FileSystemStorage(dir_path)
        input_filename = fs.save(image.name, image)
        input_path = os.path.join(dir_path,fs.path(input_filename))

        output_path = api_main(input_path)

        context = {
                    'output_path' : output_path
                }
        return render(request, 'web/download.html', context)
    
    context = {
            'form' : ImageUploadForm()
        }
    return render(request, 'web/upload.html', context)


def download(request, path):
    abs_path = os.path.join(settings.MEDIA_ROOT, 'output', path)
    if os.path.exists(abs_path):
        with open(abs_path, 'rb') as fh:
            response = HttpResponse(fh, content_type="application/force-download")
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(path)
            return response
    raise Http404
