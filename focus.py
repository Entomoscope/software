#! /usr/bin/python3
import os

import logging
from logging.handlers import RotatingFileHandler

import cv2
import numpy as np

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

# https://opencv.org/blog/autofocus-using-opencv-a-comparative-study-of-focus-measures-for-sharpness-assessment/
# https://blog.roboflow.com/computer-vision-camera-focus-guide/

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_' + this_script)
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

def compute_local_variance(gray, ksize=5):
    try:
        #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = cv2.blur(gray, (ksize, ksize))
        squared_mean = cv2.blur(gray**2, (ksize, ksize))
        variance = squared_mean - (mean**2)
        return np.mean(variance)
    except BaseException as e:
        logger.error(str(e))
        return None

def compute_tenengrad(gray):
    try:
        #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)  # Sobel filter in X direction
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)  # Sobel filter in Y direction
        tenengrad = np.sqrt(sobel_x**2 + sobel_y**2)  # Compute gradient magnitude
        return np.mean(tenengrad)  # Return mean gradient magnitude as focus score
    except BaseException as e:
        logger.error(str(e))
        return None

def compute_brenner_gradient(gray):
    try:
        #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        shifted = np.roll(gray, -2, axis=1)  # Shift by 2 pixels horizontally
        diff = (gray - shifted) ** 2  # Compute squared difference
        return np.sum(diff)  # Sum all differences as the focus measure
    except BaseException as e:
        logger.error(str(e))
        return None

def compute_sobel_variance(gray, ksize=3):
    try:
        #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)  # Sobel X gradient
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)  # Sobel Y gradient
        sobel_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)  # Compute gradient magnitude
        variance = np.var(gray)  # Compute variance of pixel intensities
        return np.mean(sobel_magnitude) + variance  # Combine Sobel and variance
    except BaseException as e:
        logger.error(str(e))
        return None

def compute_laplacian(gray, ksize=1):
    try:
        #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)  # Apply Laplacian filter
        return np.var(laplacian)  # Compute variance of Laplacian
    except BaseException as e:
        logger.error(str(e))
        return None

class Focus():

    def __init__(self):

        pass

    def compute_focus(self, image, method):

        if method == 'local_variance':
            focus_measure = compute_local_variance(image, ksize=5)
        if method == 'tenengrad':
            focus_measure = compute_tenengrad(image)
        if method == 'brenner_gradient':
            focus_measure = compute_brenner_gradient(image)
        if method == 'sobel_variance':
            focus_measure = compute_sobel_variance(image)
        if method == 'laplacian':
            focus_measure = compute_laplacian(image)

        return focus_measure

    def __str__(self):

        s = ''
        s += f'Local variance: {self.local_variance}\n'
        s += f'Tenengrad: {self.tenengrad}\n'
        s += f'Brenner gradient: {self.brenner_gradient}\n'
        s += f'Sobel variance: {self.sobel_variance}\n'
        s += f'Laplacian: {self.laplacian}\n'

        return s

if __name__ == '__main__':

    focus = Focus()


