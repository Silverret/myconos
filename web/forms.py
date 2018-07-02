from django import forms
from django.core.validators import validate_image_file_extension

class ImageUploadForm(forms.Form):
    image = forms.ImageField(validators=[validate_image_file_extension])