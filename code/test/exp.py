import os, sys, glob
import utils

# dictionary containing the test cases for each function 
cases = {
    "nbody" : [500, 400, 700, 900], 
}

python_path = "./experimental/numpy/cpython"

def test_numba():
    path = "./experimental/numpy/numba"

    # test nbody
    python_file, = list(glob.glob(f"{python_path}/nbody.py"))
    file, = list(glob.glob(f"{path}/nbody.py"))
    res = utils.test_outputs(
        'numba', file, python_file, cases["nbody"]
    )
    print(res)
    # --------

def test_codon():
    path = "./experimental/numpy/codon"

    # test codon 
    python_file, = list(glob.glob(f"{python_path}/nbody.py"))
    file, = list(glob.glob(f"{path}/nbody.py"))
    res = utils.test_outputs(
        'numba', file, python_file, cases["nbody"]
    )
    print(res)
    # --------
