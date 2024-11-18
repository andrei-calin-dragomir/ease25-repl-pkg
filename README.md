# EASE25-repl-pkg
This repository contains an experimental setup for a study of different python compilation methods with regards to their efficiency

## Experiment Design

**RQ1:** To what extent compilation affects the energy efficiency of Python Code?

Initial design involves two benchmarks:
1. `Control Group`: set of functions taken from the CBLG with defined characteristics
2. `Experimental Group`:  https://github.com/python/pyperformance/tree/main

### Control Group

We selected 6/7 functions from the Computer Language Benchmark Game (CLBG) following these criteria to mitigate any threat to validity related to code characteristics and to discover if they can influence our results.

1. well-defined developer profile
2. no parallelism (single-thread) 
3. no third-party library
4. execution time > 1 min to collect enough data for our results. As we use tools having granularity of 1 second.

| Name                                                                                                                | Execution Time | Memory Busy Time (s) | Notes               |
| ------------------------------------------------------------------------------------------------------------------- | -------------- | -------------------- | ------------------- |
| [spectral-norm](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-python3-8.html)    | 6 min          | 19.4                 |                     |
| [binary-trees](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-python3-8.html)      | 9 min          | 798.336              |                     |
| [fasta](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fasta-python3-8.html)                   | 259.98 sec     | 19.31                |                     |
| [k-nucleotide](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/knucleotide-python3-8.html)      | 238.78 sec     | 623.448              | mem-bound           |
| [n-body](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-python3-8.html)                  | 8 min          | 19.312               |                     |
| [mandelbrot](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-python3-3.html)         | 14 min         | 19.312               |                     |
| [fannxkuch-redux](https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-python3-8.html) | 37 min         | 19.312               | opt:do not consider |

### Subjects (Execution Modes)

| Subject | Type   | Description | Notes |
| ------- | ------ | ----------- | ----- |
| PyPy    | JIT    | compiles    | pypy3 |
| Nuitka  | AOT    | compiles    |       |
| Cython  | AOT    | compiles    |       |
| CPython | Inter. | ok          |       |


| Subject     | Type | Description | Notes                          |
| ----------- | ---- | ----------- | ------------------------------ |
| Numba       | JIT  | compiles -  | Need Major Rework of the Code  |
| Pyston-lite | JIT  |             |                                |
| mypyc       | AOT  | compiles -  |                                |
| pythran     | AOT  |             | needs directive                |
| codon       | AOT  | compiles    | Needs major rework of the code |
| pyjion      | JIT  |             |                                |

note: the modes are different: interpreted, python DSL, AOT, JIT. We describe in the discussion section but not part of this study.

#### First Experiment on the Control Group

`Runs:` 6 functions x 10 repetitions x 9 modes

`Total_Time:` 60 + 90 + 44.83 + 80 + 140 + 20 min (total cooling down) ~ 7 hours 

`Worst Case:` 7h x 9 modes = 2.6 days

NB: The functions on the CLBG were executed on a quad core. Our NUC should be more powerful.

### CheckList 

- [x] define run_table.csv (function, exec_mode, cpu_usage, execution_time, energy_usage, llc, vms, rss, etc.)
- [x] randomization
- [x] cooling down period of 2 min
- [x] warm up run: prior to the experiment run a function to warm up the machine (e.g., fibonacci.py) for 1m and then cool the machine for 30 seconds.
- [x] save the output of the functions
- [x] add validation of result for each function
- [ ] setup compilers to save intermediate files
- [ ] compile and save all scripts
- [ ] check the conditions of the testbed when idle.
- [ ] check Hyperthreading OFF
- [ ] check Turbo boost OFF (Linux Governor Powersave)

## Experiment Setup

### Metric Extraction

We use the [Experiment Runner](https://github.com/S2-group/experiment-runner) framework to automate our experiment.

The metrics we collect are as follows:
- [Perf](https://perfwiki.github.io/main/):
    - LLC Hits - Count, Percentage
    - LLC Misses - Count, Percentage
    - Cache-references - Count, Percentage
    - Cache-misses - Count, Percentage
    - LLC-loads - Count, Percentage
    - LLC-load-misses - Count, Percentage
    - LLC-stores - Count, Percentage
    - LLC-store-misses - Count, Percentage

- [Energibridge](https://github.com/tdurieux/EnergiBridge.git):
    - Per CPU:
        - Frequency - MHz
        - Temperature - Celsius
        - Usage - Percentage
    - Per Process:
        - CPU Usage - Percentage
        - Used Memory - Bytes
        - Used Swap Memory - Bytes
    - Execution Time - ms
    - Total Energy - Joules

## Installation

```bash
git clone --recursive https://github.com/andrei-calin-dragomir/ease25-repl-pkg.git
cd ./ease25-repl-pkg
poetry install
```

### Experimental Machine
```bash
cd EnergiBridge/

# Must do this on every machine reboot
sudo chgrp -R <user> /dev/cpu/*/msr
sudo chmod g+r /dev/cpu/*/msr
cargo build -r
sudo setcap cap_sys_rawio=ep target/release/energibridge
```

## Execution

```bash
poetry shell
python ./experiment-runner/experiment-runner/ RunnerConfig_execution.py
```
