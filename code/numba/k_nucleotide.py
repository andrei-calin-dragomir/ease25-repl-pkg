# The Computer Language Benchmarks Game
#   https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
#
#   Naive transliteration from bearophile's program
#   contributed by Isaac Gouy 

# from sys import stdin

from numba import njit, types
from numba.typed import List

@njit
def seq_lines(lines):
    for line in lines:
        if line.startswith(">THREE"):
            break

    #lines = []
    lines = List.empty_list(types.unicode_type)

    for line in lines:
        if line.startswith(">"):
            break
        #lines.append( line[len(line)-1] )       
        lines.append( line[:-1] )       
    return lines
    
@njit
def base_counts(bases, seq):  
    counts = {}
    size = len(seq) + 1 - bases
    for i in range(size):  
        nucleo = seq[i: i + bases]  
        if nucleo in counts:   
            counts[nucleo] += 1  
        else:
            counts[nucleo] = 1
    return counts               

@njit
def sorted_freq(bases, seq):  
    keysValues = base_counts(bases, seq).items()
    size = len(seq) + 1 - bases    
    sorted_ =  sorted(keysValues, reverse=True, key=lambda kv: kv[1])     
    return [ (kv[0], 100.0 * kv[1] / size) for kv in sorted_ ]  
      
@njit
def specific_count(code, seq):  
    return base_counts(len(code), seq).get(code,0)   
    
@njit
def main(lines):
    lines = seq_lines(lines)
    seq = "".join([s.upper() for s in lines])
        
    for base in 1,2:
        for kv in sorted_freq(base, seq):
            print(kv[0], float(int(kv[1]) * 10**3) / 10**3)
           #print("%s %.3f" % (kv[0], kv[1]))

        print()      
      
    for code in "GGT", "GGTA", "GGTATT", \
            "GGTATTTTAATT", "GGTATTTTAATTTATAGT":     
        #print("%d\t%s" % (specific_count(code, seq), code))       
        print(specific_count(code, seq),'\t',code)

with open('../functions/knucleotide_input.txt', 'r') as file:
    content = file.read()
    main(content.splitlines())
