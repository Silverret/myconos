from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'web'
urlpatterns = [
    path('', views.index, name='index'),
    re_path(r'^download/(?P<path>[\w\.]+)/$', views.download, name='download'),
]
