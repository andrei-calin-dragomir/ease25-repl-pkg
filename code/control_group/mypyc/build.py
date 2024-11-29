import glob, os
from setuptools import setup 
from mypyc.build import mypycify

def build():
    paths = glob.glob('./source/*.py', recursive=True) 
    
    setup(
        ext_modules = mypycify(paths),
        script_args = ['build_ext'],
        options={'build':{'build_lib':'build'}}
    )

if __name__ == "__main__":
    build()
