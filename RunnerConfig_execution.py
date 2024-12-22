from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from os.path import dirname, realpath

# Experiment specific imports
import time
import paramiko
import subprocess
import pandas as pd
from os import getenv, remove
from dotenv import load_dotenv
from scp import SCPClient
from collections import defaultdict
load_dotenv()

RAPL_OVERFLOW_VALUE = 262143.328850

class ExternalMachineAPI:
    def __init__(self):

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.stdin = None
        self.stdout = None
        self.stderr = None
        
        try:
            self.ssh.connect(hostname=getenv(f'HOSTNAME'), username=getenv(f'USERNAME'), password=getenv(f'PASSWORD'))
        except paramiko.SSHException:
            output.console_log_FAIL('Failed to send run command to machine!')

    def execute_remote_command(self, command : str = '', overwrite_channels : bool = True):
        try:
            # Execute the command
            if overwrite_channels:
                self.stdin, self.stdout, self.stderr = self.ssh.exec_command(command)
            else:
                self.ssh.exec_command(command)
        except paramiko.SSHException:
            output.console_log_FAIL('Failed to send run command to machine.')
        except TimeoutError:
            output.console_log_FAIL('Timeout reached while waiting for command output.')

    def copy_file_from_remote(self, remote_path, local_path):
        # Create SSH client and SCP client
        with SCPClient(self.ssh.get_transport()) as scp:
            # Copy the file from remote to local
            scp.get(remote_path, local_path, recursive=True)
        output.console_log_OK(f"Copied {remote_path} to {local_path}")

    def __del__(self):
        self.stdin.close()
        self.stdout.close()
        self.stderr.close()
        self.ssh.close()

def parse_perf_output(file_path):
    # Initialize dictionary with all data_columns as keys and default to None
    perf_data = {
        'cache-references': None, 'cache-misses': None, 'LLC-loads': None, 'LLC-load-misses': None, 'LLC-stores': None, 'LLC-store-misses': None,
        'cache-references_percent': None, 'cache-misses_percent': None, 'LLC-loads_percent': None, 'LLC-load-misses_percent': None,
        'LLC-stores_percent': None, 'LLC-store-misses_percent': None
    }
    
    # Open the file and parse each line
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Parse each line in the perf output, skip the header lines
    for line in lines[2:]:
        parts = line.split(',')
        
        # Extract event count, type, and percentage
        event_count = int(parts[0].strip()) if str(parts[0].strip()).isdigit() else None
        event_type = parts[2].split('/')[1].strip()  # Extract only the event name
        percentage = float(parts[4].strip())

        # Map to dictionary keys
        count_key = event_type
        percent_key = f"{event_type}_percent"

        # Update dictionary values
        if count_key in perf_data and percent_key in perf_data:
            perf_data[count_key] = event_count
            perf_data[percent_key] = percentage

    return perf_data

def parse_energibridge_output(file_path):
    # Define target columns
    target_columns = [
        'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 'USED_SWAP', 'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY'
    ] + [f'CPU_USAGE_{i}' for i in range(12)]

    delta_target_columns = [
        'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 'PP1_ENERGY (J)'
    ]

    # Read the file into a pandas DataFrame
    df = pd.read_csv(file_path).apply(pd.to_numeric, errors='coerce')

    # Calculate column-wise averages, ignoring NaN values and deltas from start of experiment to finish
    averages = df[target_columns].mean().to_dict()
    deltas = {}

    # Account and mitigate potential RAPL overflow during metric collection
    overflow_counter = 0
    for column in delta_target_columns:
        # Iterate and adjust values in the array
        column_data = df[column].to_numpy()
        for i in range(1, len(column_data)):
            if column_data[i] < column_data[i - 1]:
                output.console_log_WARNING(f"RAPL Overflow found:\nReading {i-1}: {column_data[i-1]}\nReading {i}: {column_data[i]}")
                overflow_counter += 1
                column_data[i:] += overflow_counter * RAPL_OVERFLOW_VALUE
        deltas[column] = column_data[-1] - column_data[0]

    return dict(averages.items() | deltas.items())

def compare_files_bash(file1, file2):
    try:
        # Run the `diff` command to compare the files
        result = subprocess.run(["diff", file1, file2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout == b""  # True if no output, False otherwise
    except subprocess.CalledProcessError:
        return False  # Files are different or an error occurred 

class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))

    # ================================ USER SPECIFIC CONFIG ================================
    """The name of the experiment."""
    name:                       str             = f"full_experiment"

    """The path in which Experiment Runner will create a folder with the name `self.name`, in order to store the
    results from this experiment. (Path does not need to exist - it will be created if necessary.)
    Output path defaults to the config file's path, inside the folder 'experiments'"""
    results_output_path:        Path            = ROOT_DIR / 'experiments'

    """Experiment operation type. Unless you manually want to initiate each run, use `OperationType.AUTO`."""
    operation_type:             OperationType   = OperationType.AUTO

    """The time Experiment Runner will wait after a run completes.
    This can be essential to accommodate for cooldown periods on some systems."""
    time_between_runs_in_ms:    int             = 120000

    # Dynamic configurations can be one-time satisfied here before the program takes the config as-is
    # e.g. Setting some variable based on some criteria
    def __init__(self):
        """Executes immediately after program start, on config load"""
        load_dotenv()
        
        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN       , self.before_run       ),
            (RunnerEvents.START_RUN        , self.start_run        ),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT         , self.interact         ),
            (RunnerEvents.STOP_MEASUREMENT , self.stop_measurement ),
            (RunnerEvents.STOP_RUN         , self.stop_run         ),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT , self.after_experiment )
        ])


        self.run_table_model                    = None  # Initialized later

        self.project_directory = "./Work/GreenLab/greenlab-python-compilation-experiment/"
        self.venv_python = f'poetry run python'

        self.metric_capturing_interval  : int   = 1000  # Miliseconds
        self.warmup_time                : int   = 60    # Seconds
        self.post_warmup_cooldown_time  : int   = 30    # Seconds

        self.subject_execution_templates = {
            'cpython'   : {
                'file_io'   : '{venv_python} {target_path}/{target}.py',
                'value_io'  : '{venv_python} {target_path}/{target}.py {input}'
            },
            'cython'    : {
                'build'     : '{venv_python} {project_directory}/control_group/{target}/build.py {project_directory}/control_group/{target}/source',
                'file_io'   : '{venv_python} -c "import sys; sys.path.insert(0, \'{target_path}/build/\'); import {target}; {target}.main()"',
                'value_io'  : '{venv_python} -c "import sys; sys.path.insert(0, \'{target_path}/build/\'); import {target}; {target}.main({input})"'
            },
            'nuitka'    : {
                'build'     : '{project_directory}/control_group/{target}/build.sh {project_directory}/control_group/cpython {project_directory}/control_group/{target}/build',
                'file_io'   : '{target_path}/build/{target}.bin',
                'value_io'  : '{target_path}/build/{target}.bin {input}'
            },
            'pypy'      : {
                'file_io'   : 'pypy3 {target_path}/{target}.py',
                'value_io'  : 'pypy3 {target_path}/{target}.py {input}'
            },
            'mypyc'     : {
                'build'     : '{venv_python} {project_directory}/control_group/{target}/build.py {project_directory}/control_group/{target}/source',
                'file_io'   : '{venv_python} -c "import sys; sys.path.insert(0, \'{target_path}/build/\'); import {target}; {target}.main()"',
                'value_io'  : '{venv_python} -c "import sys; sys.path.insert(0, \'{target_path}/build/\'); import {target}; {target}.main({input})"'
            },
            'codon'     : {
                'build'     : '{project_directory}/control_group/{target}/build.sh {project_directory}/control_group/{target}/source {project_directory}/control_group/{target}/build',
                'file_io'   : '{target_path}/build/{target} {input}',
                'value_io'  : '{target_path}/build/{target} {input}'
            },
            'numba'     : {
                'file_io'   : '{venv_python} {target_path}/{target}.py',
                'value_io'  : '{venv_python} {target_path}/{target}.py {input}'
            },
            'pythran'     : {
                'file_io'   : None,
                'value_io'  : None
            },
            'pyston-lite'    : {
                'file_io'   : None,
                'value_io'  : None
            }
        }

        self.target_inputs = {
            'spectralnorm'      : 5500,
            'binary_trees'      : 21,
            'fasta'             : 25000000,
            'k_nucleotide'      : f'{self.project_directory}/code/fasta_input.txt',
            'n_body'            : 50000000,
            'mandelbrot'        : 16000,
            'fannkuch_redux'    : 12,
        }

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("subject", ['numba', 'cpython', 'cython', 'pypy', 'codon', 'mypyc', 'nuitka'])
        factor2 = FactorModel("target", ['mandelbrot', 'spectralnorm', 'binary_trees', 'fasta', 'k_nucleotide', 'n_body', 'fannkuch_redux'])
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            repetitions=15,
            shuffle=True,
            data_columns=['cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 'LLC-stores', 'LLC-store-misses',
                          'cache-references_percent', 'cache-misses_percent', 'LLC-loads_percent', 'LLC-load-misses_percent', 'LLC-stores_percent', 'LLC-store-misses_percent',
                          'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 'PP1_ENERGY (J)', 
                          'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 'USED_SWAP',
                          'PROCESS_CPU_USAGE', 'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY',
                          'total_joules', 'execution_time'] + [f"CPU_USAGE_{i}" for i in range(12)]
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        output.console_log("Config.before_experiment() called!")
        ssh = ExternalMachineAPI()

        # Extract fasta_input.txt file
        check_command = f"[ -f {self.project_directory}/code/fasta_input.txt ] && echo 'exists' || echo 'not_exists'"
        ssh.execute_remote_command(check_command)
        check_status = ssh.stdout.readline()
        if check_status.strip() == 'not_exists':
            output.console_log("Unpacking expected results of fasta_input.txt on experimental machine...")
            extract_command = f'tar -xf {self.project_directory}/code/fasta_input.tar.xz -C {self.project_directory}/code/'
            ssh.execute_remote_command(extract_command)

        # Compile binaries for all subjects
        for target, data in self.subject_execution_templates.items():
            if data.get('build', None):
                build_command = data['build'].format_map(defaultdict(str, {'project_directory' : self.project_directory,
                                                                            'target'      : target,
                                                                            'venv_python' : self.venv_python,
                                                                            }))
                ssh.execute_remote_command(build_command)

        # Warmup machine for one minute
        output.console_log("Warming up machine using a fibonnaci sequence...")
        warmup_command = f"echo {getenv('PASSWORD')} | sudo -S {self.venv_python} {self.project_directory}/code/warmup.py 1000 & pid=$!; echo $pid"
        ssh.execute_remote_command(warmup_command)
        time.sleep(self.warmup_time)
        ssh.execute_remote_command(f"echo {getenv('PASSWORD')} | sudo -S kill {ssh.stdout.readline()}")

        # Cooldown machine
        time.sleep(self.post_warmup_cooldown_time)

        output.console_log_OK("Warmup finished. Experiment is starting now!")

    def before_run(self) -> None:
        pass

    def start_run(self, context: RunnerContext) -> None:
        output.console_log("Config.start_run() called!")

        subject = context.run_variation['subject']
        target = context.run_variation['target']
        input = self.target_inputs[context.run_variation['target']]
        
        target_path = f'{self.project_directory}/code/control_group/{subject}'

        self.external_run_dir = f'{self.project_directory}/experiments/{self.name}/{context.run_dir.name}'

        energibrige_command = f'sudo -S {self.project_directory}/EnergiBridge/target/release/energibridge --interval {self.metric_capturing_interval} --summary --output {self.external_run_dir}/energibridge.csv --command-output {self.external_run_dir}/output.txt taskset -c 0'

        # Fill command with current run values
        subject_command = self.subject_execution_templates[subject]['file_io' if isinstance(input, str) else 'value_io'].format_map(defaultdict(str, {'target_path' : target_path,
                                                                                                                                                      'target'      : target,
                                                                                                                                                      'venv_python' : self.venv_python,
                                                                                                                                                      'input'       : input
                                                                                                                                                      }))
        
        # Wrap command to fit paramiko call
        if isinstance(input, str):
            self.execution_command = f"{energibrige_command} {subject_command}< <(echo {getenv('PASSWORD')} && cat {input})"
        else:
            self.execution_command = f"echo {getenv('PASSWORD')} | {energibrige_command} {subject_command}"

        self.perf_command = f'sudo -S perf stat -x, -o {self.external_run_dir}/perf.csv -e cpu_core/cache-references/,cpu_core/cache-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/,cpu_core/LLC-stores/,cpu_core/LLC-store-misses/ -p'
        # Make directory of run on experimental machine
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f"echo {getenv('PASSWORD')} | sudo -S mkdir -p {self.external_run_dir}")
        del ssh

        output.console_log(f'Run directory on experimental machine: {self.external_run_dir}')
        output.console_log_OK('Run configuration is successful.')

    def start_measurement(self, context: RunnerContext) -> None:
        output.console_log("Config.start_measurement() called!")    
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(self.execution_command)
        output.console_log(f'Running command through energibridge with:\n{self.execution_command}')

        self.interaction_pid = int(ssh.stdout.readline())

        # Start perf monitor and attach it to the target process
        output.console_log(f'PID of run interaction: {self.interaction_pid}')
        
        perf_command = f"echo {getenv('PASSWORD')} | {self.perf_command} {str(self.interaction_pid)}"
        output.console_log(f'Running perf with:\n{perf_command}')
        ssh.execute_remote_command(perf_command, overwrite_channels=False)
        output.console_log_OK('Run has successfuly started.')

        # Energy Bridge Summary format: Energy consumption in joules: 7.630859375 for 2.0023594 sec of execution.
        next_line = ssh.stdout.readline()
        output.console_log_bold(f'Summary of energibridge: {next_line}')
        del ssh

        output.console_log_OK('Run has successfuly finished.')

    def interact(self, context: RunnerContext) -> None:
        pass

    def stop_measurement(self, context: RunnerContext) -> None:
        pass

    def stop_run(self, context: RunnerContext) -> None:
        pass

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """Parse and process any measurement data here.
        You can also store the raw measurement data under `context.run_dir`
        Returns a dictionary with keys `self.run_table_model.data_columns` and their values populated"""
        output.console_log("Config.populate_run_data() called!")


        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f'ls {self.external_run_dir}')
        files = ssh.stdout.readlines()
        for file in files:
            output.console_log_WARNING(f"This is the file on the other machine {file}")
            ssh.copy_file_from_remote(f'{self.external_run_dir}/{file.strip()}', context.run_dir)

        local_output_validation_file = f"./code/outputs/{context.run_variation['target']}.txt"
        received_output_file = f"{context.run_dir}/output.txt"
        # Check if run results are correct before storing data for the run
        if compare_files_bash(local_output_validation_file, received_output_file):
            # Extract perf output from experimental machine for current run
            perf_output = parse_perf_output(f"{context.run_dir}/perf.csv")
            energibridge_output = parse_energibridge_output(f"{context.run_dir}/energibridge.csv")

            # Remove output files because they take a lot of space
            remove(received_output_file)
            ssh.execute_remote_command(f"echo {getenv('PASSWORD')} | sudo -S rm {self.external_run_dir}/output.txt")
            del ssh
            return dict(perf_output.items() | energibridge_output.items())
        else:
            output.console_log_FAIL(f'Target function did not return the expected result.')
            del ssh
            return None

    def after_experiment(self) -> None:
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f"echo {getenv('PASSWORD')} | sudo -S rm -r {self.project_directory}/experiments")
        del ssh

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None