import customtkinter as ctk
import platform
from os import getcwd
from os.path import dirname, exists, join
from MapStitching.gui import MainFrame

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.app_name = "MapStitching"
        self.version = "0.1.0"
        self.geometry("800x300")
        self.title(f"{self.app_name} {self.version}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme('dark-blue')
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)

        if platform.system() == "Windows":
            self.installdir = getcwd()
        elif platform.system() == "Linux":
            self.installdir = dirname(__file__)
        print("installdir:",self.installdir, exists(self.installdir))
        self.share_dir = join(dirname(self.installdir), "share")
        if not exists(self.share_dir):
            self.share_dir = join(dirname(dirname(self.installdir)), "share")
        print("share dir", self.share_dir, exists(self.share_dir))

        self.main_frame = MainFrame(master = self, root = self)
        self.main_frame.grid(row = 0, column = 0, sticky = "nswe")


if __name__ == "__main__":
    app = App()
    if platform.system().startswith('Linux'):
        app.option_add('*TkChooseDir*foreground', 'gray10')
        app.option_add('*TkFDialog*foreground', 'gray10')

    def on_close():
        app.destroy()
        exit(0)

    #start application
    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()
