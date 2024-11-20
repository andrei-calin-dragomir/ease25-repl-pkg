import glob, os
from setuptools import setup 
from Cython.Build import cythonize

def build():
    paths = glob.glob('../python/*.py', recursive=True)
    setup(
        ext_modules = cythonize(paths, build_dir="build"),
        script_args = ['build_ext'],
        options={'build':{'build_lib':'build'}}
    )

if __name__ == "__main__":
    build()
