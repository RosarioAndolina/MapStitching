from distutils.core import setup
import platform
import subprocess
from sys import executable
from os.path import join
from shutil import copyfile

__version__ = "0.1.0"
program_name = "MapStitching"
pname_lower = program_name.lower()

if __name__ == '__main__':
    
    requirements = ["wheel", "customtkinter", "scipy", "matplotlib", "opencv-python", "stitching"]
    
    if platform.system() == "Windows":
        try:
            import kiwisolver
        except:
            requirements += ['msvc-runtime']
    
    with open(f'{program_name}.bat', 'w') as f:
        f.write(f"\"{executable}\" {pname_lower}.py")
    
    scripts = [f"{pname_lower}.py",f"{pname_lower}.bat"] if platform.system() == 'Windows' else [f"{pname_lower}.py"]
    
    setup(name=program_name,
        version=__version__,
        description='XRF elemental maps stitcher',
        author='Rosario Andolina',
        author_email='andolinarosario@gmail.com',
        packages = [program_name],
        package_dir = {program_name : program_name},
        # package_data = {program_name : ['*.pyd']},
        # data_files = [(f"share/{program_name}", ["share/icon.ico"])],
        install_requires = requirements,
        scripts = scripts)
