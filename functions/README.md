# README

## Benchmarks
We selected 6/7 functions from the Computer Language Benchmark Game (CLBG) following these criteria to mitigate any threat to validity related to the characteristics of the code:

1. well-defined developer profile
2. no parallelism (single-thread) 
3. no third-party library
4. execution time > 1 min to collect enough data for our resuls. As we use tools having granularity of 1 second.

Selected Functions Performance Profile on CLBG:

| Name                                                                                                                | Execution Time       | Memory Busy Time (s) |   Notes             |
|-------------------------------------------------------------------------------------------------------------------- |----------------------|----------------------| --------------------|
| [spectral-norm](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-python3-8.html)    | 6 min                | 19.4                 |                     |
| [binary-trees](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-python3-8.html)      | 9 min                | 798.336              |                     |
| [fasta](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fasta-python3-8.html)                   | 259.98 sec           | 19.31                |                     |
| [k-nucleotide](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/knucleotide-python3-8.html)      | 238.78 sec           | 623.448              | mem-bound           |
| [n-body](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-python3-8.html)                  | 8 min                | 19.312               |                     |	
| [mandelbrot](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-python3-3.html)         | 14 min               | 19.312               |                     |  
| [fannxkuch-redux](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-python3-8.html) | 37 min               | 19.312               | opt:do not consider |  

### Competitors

[PyPerformanceBenchmark](https://github.com/python/pyperformance/tree/main) used by Python contributors to test Python's features.

[PyPyBenchmark](https://foss.heptapod.net/pypy/benchmarks)

Some of their functions use third-party libraries, such as Djago. Probably not suitable for us as we want to see how the compilers optimized the code.

[RosettaCode](https://foss.heptapod.net/pypy/benchmarks)

## Compilers 

`execution_modes = {Codon, Nuitka, PyPy, Numba, Cython, Pyston, mypyc, pythran, native (CPython)}`
`not_considered = {Mojo, Taichi, Regaz}`

note: the modes are different: interpreted, python DSL, AOT, JIT. We describe in the discussion section but not part of this study.

## First Experiment

### RQ1: Energy Usage

```
Runs: 6 functions x 10 repetitions x 9 modes 
Total_Time: 60 + 90 + 44.83 + 80 + 140 + 20 min (total cooling down) ~ 7 hours  
Worst Case: 7h x 9 modes = 2.6 days 
```

### RQ2: Performance
Paper done

If we have time:

### RQ3: Multithreading 
Take the multithreaded version of the above functions and rerun the experiment

### RQ4: vs C++ 
Take the C++ version of the above functions and rerun the experiment



