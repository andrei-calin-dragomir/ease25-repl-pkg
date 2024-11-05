# greenlab-python-compilation-experiment
This repository contains an experimental setup for a study of different python compilation methods with regards to their efficiency

## Subjects
- [Nuitka](https://nuitka.net/user-documentation/tutorial-setup-and-build.html)

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

- [time](https://docs.python.org/3/library/time.html):
    - Execution Time - ms

## Installation

```bash
git clone --recursive https://github.com/andrei-calin-dragomir/greenlab-python-compilation-experiment.git
cd ./greenlab-python-compilation-experiment
python3 -m venv venv
source ./venv/bin/activate
```

### Orchestrator Machine
```bash
pip install -r requirements.txt
```

### Experimental Machine
```bash
pip install -r subject_requirements.txt
```

## Execution

```bash
source ./venv/bin/activate
python /experiment-runner/experiment-runner/ RunnerConfig.py
```