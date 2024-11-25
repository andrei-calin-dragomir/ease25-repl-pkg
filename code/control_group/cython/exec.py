import sys
sys.path.append('build')

import binary_trees as bn
import fannkuch_redux as fr
import fasta as fa
import mandelbrot as mb
import nbody as nb
import spectralnorm as sn
import k_nucleotide as kn

bn.main(10) # binary_trees
#fr.fannkuch(5) # fannkuch 
#fa.main(1000) # fasta
#
## k_nucleotide
#with open('../functions/knucleotide_input.txt', 'r') as file:
#    content = file.read()
#    kn.main(content.splitlines())

#mb.main(500) # mandelbrot
#nb.nbody(500) # nbody
#sn.main(500) # spectralnorm
