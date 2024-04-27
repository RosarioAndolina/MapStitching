import cv2 as cv

from skimage.exposure import equalize_adapthist
from skimage.filters import sobel

from os.path import join, splitext, basename, exists
from glob import glob

from PIL import Image as pilImage, ImageOps
from PIL import ImageEnhance

from numpy import array, uint8, float32

def load_images(img_list):
    images = [cv.imread(m) for m in img_list]
    return images

def load_directories(dir_list, image_type = 'tiff'):
    maps = {}
    if "." in image_type:
        image_type = image_type.replace(".", "").strip()
    for dir in dir_list:
        key = dir#basename(dir)
        map_list = glob(join(dir,f'*.{image_type}'))
        if not map_list:
            raise FileNotFoundError(f"{image_type} files not found")
        for m in map_list:
            line,_ = splitext(basename(m))
            if key not in maps:
                maps[key] = {}
                maps[key][line] = m
            else:
                maps[key][line] = m
    return maps

def select_line(maps, line = 'data'):
    maps_list = []
    for k in maps:
        map = maps[k].get(line)
        if not map:
            raise ValueError(f"{line} line not found")
        maps_list.append(map)

    return maps_list

def contrast_image(image, factor = 2):
    image = pilImage.fromarray(image)
    image = ImageEnhance.Contrast(image).enhance(factor)
    image = array(image)
    return image

def invert_image(image):
    image  = pilImage.fromarray(image)
    image = ImageOps.invert(image)
    image = array(image)
    return image

def equalize_image(image, clip_limit = 0.01):
    image = image.astype(float)
    _max = image.max()
    image = image/_max
    for i in range(image.shape[2]):
        image[...,i] = equalize_adapthist(image[...,i], clip_limit=clip_limit)

    out = (image/image.max()*_max).astype(uint8)
    return out

def apply_sobel(image):
    image = image.astype(float32)
    _max = image.max()
    for i in range(image.shape[2]):
        image[...,i] = sobel(image[...,i])
    image = image/image.max()*_max
    return image.astype(uint8)

def resize(image,  scale):
    height, width = image.shape[:2]
    new_shape = (int(width*scale),int(height*scale))
    return cv.resize(image, new_shape, cv.INTER_LINEAR_EXACT)