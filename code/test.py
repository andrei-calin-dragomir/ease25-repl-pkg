import sys, os, unittest, io, glob, re
from contextlib import redirect_stdout
import subprocess as sb

# functions executed using the Python interpreter. They represent the horacle for this test case.
from control_group.python import (
    binary_trees as pybt,
    fannkuch_redux as pyfr,
    fasta as pyfa, k_nucleotide as pykn,
    mandelbrot as pyma,
    nbody as pynb,
    spectralnorm as pysp
)

def read_kn_inputs():
    files = glob.glob('./control_group/functions/knucleotide_inputs/*.txt')
    inputs = []
    for x in files:
        with open(x, 'r') as file:
            content = file.read()
            inputs.append(content.splitlines())
    return inputs

# tools to execute the code
modes = ["codon", "numba", "cython", "mypyc", "nuitka", "python"]
# dictionary containing the inputs to test each function
cases = {
    "binary_trees" : [4, 6, 8, 10],
    "fannkuch_redux" : [4, 5, 6, 7],
    "fasta" : [1000, 500, 1200, 800],
    "k_nucleotide" : read_kn_inputs(),
    "mandelbrot" : [500, 600, 300, 800],
    "nbody" : [500, 400, 700, 900], 
    "spectralnorm" : [500, 231, 623, 450]
}

def capture_stdout(func, *args):
    f = io.StringIO()
    with redirect_stdout(f):
        func(*args)
    return f.getvalue()

def compare_strings(str1, str2):
    filtered_str1 = re.sub(r"\s+", "", str1)
    filtered_str2 = re.sub(r"\s+", "", str2)

    return filtered_str1 == filtered_str2 

def check_output(inputs, fun_to_test, fun_horacle): 
    for x in inputs:
        output = capture_stdout(fun_to_test, x) 
        expected_output = capture_stdout(fun_horacle, x) 

        if not compare_strings(output, expected_output):
            print(
                f"The outputs of {fun_to_test.__module__} and {fun_horacle.__module__} MISMATCH on input {x}"
            )
            return False
    print(
        f"The outputs of {fun_to_test.__module__} and {fun_horacle.__module__} MATCH for each input"
    )

    return True 

def check_codon_numerical_output(output, expected_output):
    '''some compilers have different implementations of mathematical operations
    such as division and multiplication.  Since Codon, rounds some digits 
    for division, we manually check (only for numerical output and only for testing) 
    wheather the rounded numbers correspond to those generated 
    by the interpreted version of the same function
    '''
    output = output.split()
    expected_output = expected_output.split()
    
    return any(abs(float(x) - float(y)) <= 0.0002 for x,y in zip(output, expected_output))

def normalize_string(s):
    # Split the string into parts
    parts = s.split()
    
    # Normalize each part
    normalized_parts = []
    for part in parts:
        # Check if the part can be converted to a float
        try:
            # Convert to float and then back to string to normalize
            normalized_part = str(float(part))
            normalized_parts.append(normalized_part)
        except ValueError:
            # If it can't be converted, keep it as is
            normalized_parts.append(part)
    
    # Join the normalized parts back into a string
    return ' '.join(normalized_parts)

def check_knucleotide_output(output, expected_output):
    output = list(map(normalize_string, output.split()))
    expected_output = list(map(normalize_string, expected_output.split())) 
    return any(x == y for x,y in zip(output, expected_output))

def check_output_subprocess(inputs, fun_to_test, fun_horacle, inputs_horacle=""): 
    # users can provide custom inputs for the horacle
    if not inputs_horacle:
        inputs_horacle = inputs

    for x, y in zip(inputs, inputs_horacle):
        output =  sb.run(
            [
                f"./control_group/codon/codon_tests/build/{fun_to_test}", str(x)
            ], capture_output=True
        ).stdout.decode('utf-8')
        expected_output = capture_stdout(fun_horacle, y) 

        if fun_to_test == 'nbody' or fun_to_test == 'spectralnorm':
            # special case in case codon uses another precision for floats
            if not check_codon_numerical_output(output, expected_output):
                print(
                    f"The outputs of {fun_to_test} and {fun_horacle.__module__} MISMATCH",
                    f"on input {x}"
                )
                return False

        elif fun_to_test == 'k_nucleotide':
            if not check_knucleotide_output(output, expected_output):
                print(
                    f"The outputs of {fun_to_test} and {fun_horacle.__module__} MISMATCH",
                    f"on input {x}"
                )
                return False 

        elif not compare_strings(output, expected_output):
            print(
                f"The outputs of {fun_to_test} and {fun_horacle.__module__} MISMATCH",
                f"on input {x}"
            )
            return False 
    print(
        f"The outputs of {fun_to_test} and {fun_horacle.__module__} MATCH"
    )

    return True 

def test_numba():
    from control_group.numba import (
        binary_trees as nbbt,
        fannkuch_redux as nbfr,
        fasta as nbfa,
        k_nucleotide as nbkn,
        mandelbrot as nbma,
        nbody as nbnb,
        spectralnorm as nbsp
    )

    check_output(cases["binary_trees"], nbbt.main, pybt.main)
    check_output(cases["fannkuch_redux"], nbfr.main, pyfr.main)
    check_output(cases["fasta"], nbfa.main, pyfa.main)
    check_output(cases["k_nucleotide"], nbkn.main, pykn.main)
    check_output(cases["mandelbrot"], nbma.main, pyma.main)
    check_output(cases["nbody"], nbnb.main, pynb.main)
    check_output(cases["spectralnorm"], nbsp.main, pysp.main)

def test_cython():
    import sys
    sys.path.append('./control_group/cython/build')

    import binary_trees as cybt
    import fannkuch_redux as cyfr
    import fasta as cyfa
    import k_nucleotide as cykn
    import mandelbrot as cyma
    import nbody as cynb
    import spectralnorm as cysp

    check_output(cases["binary_trees"], cybt.main, pybt.main)
    check_output(cases["fannkuch_redux"], cyfr.main, pyfr.main)
    check_output(cases["fasta"], cyfa.main, pyfa.main)
    check_output(cases["k_nucleotide"], cykn.main, pykn.main)
    check_output(cases["mandelbrot"], cyma.main, pyma.main)
    check_output(cases["nbody"], cynb.main, pynb.main)
    check_output(cases["spectralnorm"], cysp.main, pysp.main)

def test_mypyc():
    import sys
    sys.path.append('./control_group/mypyc/build')

    import binary_trees as mybt
    import fannkuch_redux as myfr
    import fasta as myfa
    import k_nucleotide as mykn
    import mandelbrot as myma
    import nbody as mynb
    import spectralnorm as mysp

    check_output(cases["binary_trees"], mybt.main, pybt.main)
    check_output(cases["fannkuch_redux"], myfr.main, pyfr.main)
    check_output(cases["fasta"], myfa.main, pyfa.main)
    check_output(cases["k_nucleotide"], mykn.main, pykn.main)
    check_output(cases["mandelbrot"], myma.main, pyma.main)
    check_output(cases["nbody"], mynb.main, pynb.main)
    check_output(cases["spectralnorm"], mysp.main, pysp.main)

## Test Codon 
def test_codon():
    check_output_subprocess(cases["binary_trees"], "binary_trees", pybt.main)
    check_output_subprocess(cases["fannkuch_redux"], "fannkuch_redux", pyfr.main)
    check_output_subprocess(cases["fasta"], "fasta", pyfa.main)
    check_output_subprocess(
        glob.glob('./control_group/functions/knucleotide_inputs/*.txt'),
        "k_nucleotide",
        pykn.main,
        inputs_horacle=cases["k_nucleotide"]
    )
    check_output_subprocess(cases["mandelbrot"], "mandelbrot", pyma.main)
    check_output_subprocess(cases["nbody"], "nbody", pynb.main)
    check_output_subprocess(cases["spectralnorm"], "spectralnorm", pysp.main)

def run_tests(flag):
    if flag == "all":
        for mode in modes[:-1]:
            globals()[f'test_{mode}']()
    elif flag in modes:
        globals()[f'test_{flag}']()
    else:
        print(f"Invalid flag: {flag}. Please use one of the following: {', '.join(modes)}.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <flag>")
        sys.exit(1)
    flag = sys.argv[1]
    run_tests(flag)
