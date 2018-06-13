

import numpy as np
import cv2

class ClassicImageProcessor():
    """
    A very simple image processor

    An image process is X steps :
    - Background suppression (dummy one)
    - Conversion to grayscale
    - LoG 
    - TOZERO Threshold with fixed value
    - Adaptative Threshold
    - Gaussian Blur

    - ConnectedComponents to extract the ROI list
    """

    def __init__(self):
        pass

    def predict(self, X):
        """
        All operations are done inplace to save memory space.
        """
        Y = []
        for img in X:
            # Background suppression
            img = self._suppress_background(img)
            # Convert to grayscale
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            # LoG Filter
            img = self._LoG_filter(img)
            # TOZERO Threshold
            _, img = cv2.threshold(img, 25, 255, cv2.THRESH_TOZERO)
            # Adaptative Threshold
            img = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,11,0)
            # Median Blur
            img = cv2.medianBlur(img, 5)
            # ConnectedComponents
            _, img = cv2.connectedComponents(img)
            Y.append(img)
        return Y


    def _suppress_background(self, img):
        # D'abord on supprime le background
        background_top = np.mean(img[:,0:10,:], axis=1)
        background_bot = np.mean(img[:,-10:,:], axis=1)
        background = (background_top + background_bot) / 2

        img = img - background
        return cv2.convertScaleAbs(img)

    def _LoG_filter(self, img):
        kernel = np.array([[1,1,1],
                           [1,-8,1],
                           [1,1,1]])
        img = cv2.GaussianBlur(img, (5,5), 0)
        laplacian = cv2.filter2D(img,cv2.CV_32F,kernel)
        img = np.float32(img)
        return cv2.convertScaleAbs(img - laplacian)


if __name__ == '__main__':
    from utils import get_images_from_tif

    processor = ClassicImageProcessor()

    images = get_images_from_tif('.//data//Composite_01.tif')[0:2]

    results = processor.predict(images)

    for k, img in enumerate(results):
        im = np.where(img != 0, 255, 0)
        cv2.imwrite(".//data//{}.tif".format(k+1), im)

    