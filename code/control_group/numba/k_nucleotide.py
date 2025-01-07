from numba import njit, types
from numba.typed import List
from numba.typed import Dict
from sys import stdin

@njit
def seq_lines(input_lines):
    i = 0
    for line in input_lines:
        i += 1
        if line.startswith(">THREE"):
            break

    lines = List.empty_list(types.unicode_type)
    for line in input_lines[i:]:
        if line.startswith(">"):
            break
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
    sorted_ = sorted(keysValues, reverse=True, key=lambda kv: kv[1])
    return [ (kv[0], 100.0 * kv[1] / size) for kv in sorted_ ]  
    # return [ (kv[0], 100.0 * kv[1] / size) for kv in keysValues ]  
      
@njit
def specific_count(code, seq):  
    return base_counts(len(code), seq).get(code,0)   
    
@njit
def process(lines):
    parsed_lines = seq_lines(lines)
    seq = "".join([s.upper() for s in parsed_lines])
    
    lines = List.empty_list(types.unicode_type)

    for base in 1,2:
        for kv in sorted_freq(base, seq):
            print(kv[0], float(int(kv[1]) * 10**3) / 10**3)
        print()
      
    for code in "GGT", "GGTA", "GGTATT", \
            "GGTATTTTAATT", "GGTATTTTAATTTATAGT":     
        print(specific_count(code, seq),'\t',code)

def main():
    # Read input lines from stdin
    input_lines = List([line for line in stdin])
    
    # Process the data using Numba functions
    process(input_lines)

if __name__ == '__main__':
    main()
