from .imagestitcher import ImageStitcher
from .utils import (load_directories, select_line, contrast_image, load_images,
                           equalize_image, apply_sobel, resize, invert_image)

import customtkinter as ctk

class MainFrame(ctk.CTkFrame):
    def __init__(self, *args, root = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root
        self.root.main_frame = self
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid(row = 0, column = 0, sticky = "nswe")