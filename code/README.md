# Structure 
Subdirectories in this folder contain the code that conforms to each execution mode. Folders referring to AOT execution modes, such as `cython` and `mypyc`, include scripts to build the code contained in the `python` folder.

As code needed to be changed to be compliant to specific compilers (e.g., `numba` and `codon`), we slightly changed the code of the original functions to reduce the differences between the original source code and that suitable specific execution modes. Therefore, for transparency, you can find the original source code in the `functions` folder and the modified version in the `python` folder.
