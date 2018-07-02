import numpy as np
import cv2
from PIL import Image

def get_images_from_tif(file):
    """
    Read a multi-pages TIF file.

    :param: file : File object, pathlib.Path object or filename (string)
    
    :return: list of images inside the TIF file
    """
    multi_img = Image.open(file)
    images_list = []
    for k in range(multi_img.n_frames):
        multi_img.seek(k)
        images_list.append(np.array(multi_img))
    return images_list

def get_rois_from_markers(markers, frame_position=0):
    """
    #TODO
    """
    rois = []
    for k in range(markers.max()):
        mask = np.uint8(np.where(markers==k+1,1,0))
        _,cnt,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = np.reshape(cnt[0], (-1,2))
        y_coords = cnt[:,0]
        x_coords = cnt[:,1]
        from api.utils.roi import ROIShape
        roi = ROIShape(x_coords, y_coords, "roi-{:04d}-{:04d}".format(frame_position, k), frame_position)
        rois.append(roi)
    return rois
        



