import sys

def seq_lines(input_lines):
    i = 0
    for line in input_lines:
        i += 1
        if line.startswith(">THREE"):
            break
    lines : list[str] = []
    for line in input_lines[i:]:
        if line.startswith(">"):
            break
        lines.append( line[:-1] )       
    return lines

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

def sorted_freq(bases, seq):  
    keysValues = base_counts(bases, seq).items()
    size = len(seq) + 1 - bases    
    sorted_ =  sorted(keysValues, reverse=True, key=lambda kv: kv[1])     
    return [ (kv[0], 100.0 * kv[1] / size) for kv in sorted_ ]  
    # return [ (kv[0], 100.0 * kv[1] / size) for kv in keysValues ]  

def specific_count(code, seq):  
    return base_counts(len(code), seq).get(code,0)   
    
def main(lines):
    lines = seq_lines(lines)
    seq = "".join([s.upper() for s in lines])
        
    for base in 1,2:
        for kv in sorted_freq(base, seq):
            print(f"{kv[0]} {(float(int(kv[1]) * 10**3) / 10**3):.1f}")
        print()

    for code in "GGT", "GGTA", "GGTATT", \
            "GGTATTTTAATT", "GGTATTTTAATTTATAGT":     
        print(specific_count(code, seq),'\t',code)

with open(sys.argv[1]) as file:
    content = file.readlines()
    main(content)
