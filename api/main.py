import os

from PIL import Image
import numpy as np

from django.conf import settings

from .utils.utils import get_rois_from_markers, get_images_from_tif
from .utils.roi import ROIEncoder
from .classicImageProcessor import ClassicImageProcessor

def main(input_file_path):

    fullfilename = os.path.basename(input_file_path)
    filename, ext = os.path.splitext(fullfilename)

    if ext == '.tif':
        images = get_images_from_tif(input_file_path)
    else:
        return None

    processor = ClassicImageProcessor()

    markers_list = processor.predict(images)

    rois = []
    for k, markers in enumerate(markers_list):
        rois += get_rois_from_markers(markers, k+1)

    encoder = ROIEncoder()

    
    output_file_path = "{}_rois.zip".format(filename)
    abs_path = os.path.join(settings.MEDIA_ROOT, 'output', output_file_path)
    encoder.write_zip(abs_path, rois)

    return output_file_path