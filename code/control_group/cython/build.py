import glob, os, sys
from setuptools import setup 
from Cython.Build import cythonize

def build(source):
    paths = glob.glob(f'{source}/*.py', recursive=True)
    setup(
        ext_modules = cythonize(paths, build_dir="build"),
        script_args = ['build_ext'],
        options={'build':{'build_lib':'build'}}
    )

if __name__ == "__main__":
    build(sys.argv[1])