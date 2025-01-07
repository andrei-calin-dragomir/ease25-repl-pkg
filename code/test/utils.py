import sys, os, io, glob, re, logging
from contextlib import redirect_stdout
import subprocess as sb

"""
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

def capture_stdout(func, *args):
    f = io.StringIO()
    with redirect_stdout(f):
        func(*args)
    return f.getvalue()

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

"""

def build_cmd(compiler, compiler_fun, python_fun, input):
    #["codon", "numba", "cython", "mypyc", "nuitka", "python"]
    commands = {
        'numba' : ['python', str(compiler_fun), str(input)],
        'python' : ['python', str(python_fun), str(input)]
    }

    return commands[compiler], commands['python']

def test_outputs(
        compiler, compiler_fun, python_fun, inputs
    ):
    for x in inputs:
        cmd1, cmd2 = build_cmd(
            compiler, compiler_fun, python_fun, x
        )
        logging.debug(cmd1, cmd2)
        if check_output(cmd1, cmd2) == False:
            return False
    return True

def check_output(cmd1, cmd2):
    result1 = sb.run(cmd1, capture_output=True, text=True)
    result2 = sb.run(cmd2, capture_output=True, text=True)

    if result1.stdout == result2.stdout:
        return True
    else:
        return False
