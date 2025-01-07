import sys, logging, importlib

# compilers 
modes = ["codon", "numba", "cython", "mypyc", "nuitka", "python"]
groups = ['control', 'exp']

# captures the flags and execute the code to test the code for a given compiler
def run_tests(group, compiler):
    if group not in groups:
        logging.error(f"Invalid group: {group}. Please use one of the following: {', '.join(groups)}.")

    if compiler in modes:
        # import modules and execute the corresponding test function
        module = importlib.import_module(group)
        function = getattr(module, f'test_{compiler}')
        result = function()
    else:
        logging.error(f"Invalid compiler: {compiler}. Please use one of the following: {', '.join(modes)}.")

if __name__ == "__main__":
    if len(sys.argv) != 4 and "-m" not in sys.argv:
        logging.error("Usage: python script.py -m <group> <compiler>")
        sys.exit(1)

    group = sys.argv[2]
    compiler = sys.argv[3] 

    run_tests(group, compiler)
