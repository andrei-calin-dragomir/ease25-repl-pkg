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
from os import getenv
from dotenv import load_dotenv
from scp import SCPClient
from collections import defaultdict

class ExternalMachineAPI:
    def __init__(self):
        load_dotenv()

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.stdin = None
        self.stdout = None
        self.stderr = None
        
        try:
            self.ssh.connect(hostname=getenv('HOSTNAME'), username=getenv('USERNAME'), password=getenv('PASSWORD'))
        except paramiko.SSHException:
            print('Failed to send run command to machine!')

    def execute_remote_command(self, command : str, arg : Union[int, str] = None, arg_from_file : bool = False, overwrite_channels : bool = True):
        try:
            # Wrap command to fit paramiko call
            if arg:
                if arg_from_file:
                    wrapped_command = f"{command}< <(echo {getenv('PASSWORD')} && cat {arg})" if command.startswith('sudo') else f'{command} <{arg}'
                if not arg_from_file:
                    wrapped_command = f"echo {getenv('PASSWORD')} | {command} {arg}" if command.startswith('sudo') else f'{command} {arg}'
            else:
                wrapped_command = f"echo {getenv('PASSWORD')} | {command}" if command.startswith('sudo') else command

            # Execute the command
            if overwrite_channels:
                self.stdin, self.stdout, self.stderr = self.ssh.exec_command(wrapped_command)
            else:
                self.ssh.exec_command(wrapped_command)
            return wrapped_command
        except paramiko.SSHException:
            print('Failed to send run command to machine!')
        except TimeoutError:
            print('Timeout reached while waiting for command output.')

    def copy_file_from_remote(self, remote_path, local_path):
        # Create SSH client and SCP client
        with SCPClient(self.ssh.get_transport()) as scp:
            # Copy the file from remote to local
            scp.get(remote_path, local_path, recursive=True)
        print(f"Copied {remote_path} to {local_path}")

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
    
    target_columns = {
        'CPU_USAGE_0', 'CPU_USAGE_1', 'CPU_USAGE_10', 'CPU_USAGE_11', 'CPU_USAGE_12', 'CPU_USAGE_13', 'CPU_USAGE_14', 'CPU_USAGE_15',
        'CPU_USAGE_2', 'CPU_USAGE_3', 'CPU_USAGE_4', 'CPU_USAGE_5', 'CPU_USAGE_6', 'CPU_USAGE_7', 'CPU_USAGE_8', 'CPU_USAGE_9',
        'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 'PP1_ENERGY (J)', 
        'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 'USED_SWAP',
        'PROCESS_CPU_USAGE', 'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY'
    }

    # Open the file and parse each line
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Extract the header and rows from the data
    header = lines[0].strip().split(',')
    rows = [line.strip().split(',') for line in lines[1:]]

    # Filter header to include only target columns and find their indices
    filtered_indices = [i for i, col in enumerate(header) if col in target_columns]
    filtered_header = [header[i] for i in filtered_indices]

    # Initialize a dictionary to store sums and counts for each column
    totals = {col: 0.0 for col in filtered_header}
    counts = len(rows)  # Total number of data rows

    # Sum each relevant column
    for row in rows:
        for i in filtered_indices:
            try:
                # Convert value to float and add to the respective total
                totals[header[i]] += float(row[i])
            except ValueError:
                # Skip if value is not a valid float
                continue

    # Calculate the average for each filtered column and return as dictionary
    averages = {col: (totals[col] / counts) for col in filtered_header if counts > 0}
    return averages

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
    name:                       str             = "execution_experiment"

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

        self.metric_capturing_interval  : int   = 1000  # Miliseconds
        self.warmup_time                : int   = 60    # Seconds
        self.post_warmup_cooldown_time  : int   = 30    # Seconds

        self.subject_execution_templates = {
            'cpython'    : '{python_venv} {target_path}/{target}.py',
            'cython'    : '{target_path}/functions/{target}', # TODO 
            'pypy'      : None, # TODO
            'nuitka'    : '{target_path}/{target}/{target}.bin',
            'numba'     : None,
            'codon'     : None,
            'mypyc'     : None,
        }

        self.target_inputs = {
            'spectralnorm'      : 5500,
            'binary_trees'      : 21,
            'fasta'             : 25000000,
            'k_nucleotide'      : './ease25-repl-pkg/code/fasta_input.txt',
            'n_body'            : 50000000,
            'mandelbrot'        : 16000,
            'fannkuch_redux'    : 12,
        }

        self.python_venv_path = f'./ease25-repl-pkg/venv/bin/python'
  
        self.run_directory_template = './ease25-repl-pkg/experiments/{name}/{run_directory_name}'

        self.energibrige_command_template = 'sudo -S ./ease25-repl-pkg/EnergiBridge/target/release/energibridge --interval {metric_capturing_interval} --summary --output {run_directory}/energibridge.csv --command-output {run_directory}/output.txt taskset -c 0 {run_command}'
        self.perf_command_template= 'sudo -S perf stat -x, -o {run_directory}/perf.csv -e cpu_core/cache-references/,cpu_core/cache-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/,cpu_core/LLC-stores/,cpu_core/LLC-store-misses/ -p '

        self.intermediary_results = {'total_joules' : None, 'execution_time' : None}

        output.console_log("Custom config loaded")

    # TODO Update Runtable
    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("subject", ['cpython']) # 'cython', 'pypy', 'numba', 'codon', 'mypyc', 'nuitka'
        factor2 = FactorModel("target", ['mandelbrot']) # 'spectralnorm', 'binary_trees', 'fasta', 'k_nucleotide', 'n_body', 'fannkuch_redux'
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            repetitions=1,
            exclude_variations=[],
            data_columns=['cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 'LLC-stores', 'LLC-store-misses',
                          'cache-references_percent', 'cache-misses_percent', 'LLC-loads_percent', 'LLC-load-misses_percent', 'LLC-stores_percent', 'LLC-store-misses_percent',
                          'CPU_USAGE_0', 'CPU_USAGE_1', 'CPU_USAGE_2', 'CPU_USAGE_3', 'CPU_USAGE_4', 'CPU_USAGE_5', 'CPU_USAGE_6', 'CPU_USAGE_7', 'CPU_USAGE_8', 'CPU_USAGE_9', 'CPU_USAGE_10', 'CPU_USAGE_11', 'CPU_USAGE_12', 'CPU_USAGE_13', 'CPU_USAGE_14', 'CPU_USAGE_15',
                          'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 'PP1_ENERGY (J)', 
                          'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 'USED_SWAP',
                          'PROCESS_CPU_USAGE', 'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY',
                          'total_joules', 'execution_time']
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        output.console_log("Config.before_experiment() called!")
        ssh = ExternalMachineAPI()

        # Extract fasta_output.txt file
        check_command = f"[ -f ./ease25-repl-pkg/code/fasta_input.txt ] && echo 'exists' || echo 'not_exists'"
        ssh.execute_remote_command(check_command)
        check_status = ssh.stdout.readline()
        if check_status.strip() == 'not_exists':
            output.console_log("Unpacking expected results of fasta.txt on experimental machine...")
            extract_command = 'tar -xf ./ease25-repl-pkg/code/outputs/fasta_input.tar.xz -C ./ease25-repl-pkg/code/'
            ssh.execute_remote_command(extract_command)

        # Extract fasta_output.txt file
        check_command = f"[ -f ./ease25-repl-pkg/code/outputs/fasta_input.txt ] && echo 'exists' || echo 'not_exists'"
        ssh.execute_remote_command(check_command)
        check_status = ssh.stdout.readline()
        if check_status.strip() == 'not_exists':
            output.console_log("Unpacking expected results of fasta_input.txt on experimental machine...")
            extract_command = 'tar -xf ./ease25-repl-pkg/code/outputs/fasta_input.tar.xz -C ./ease25-repl-pkg/code/'
            ssh.execute_remote_command(extract_command)

        # Warmup machine for one minute
        output.console_log("Warming up machine using a fibonnaci sequence...")
        warmup_command = f'{self.python_venv_path} ./ease25-repl-pkg/code/warmup.py 1000 & pid=$!; echo $pid'
        ssh.execute_remote_command(warmup_command)
        time.sleep(self.warmup_time)
        ssh.execute_remote_command(f'kill {ssh.stdout.readline()}')

        # Cooldown machine
        time.sleep(self.post_warmup_cooldown_time)

        output.console_log_OK("Warmup finished. Experiment is starting now!")

    def before_run(self) -> None:
        pass

    def start_run(self, context: RunnerContext) -> None:
        output.console_log("Config.start_run() called!")

        subject = context.run_variation['subject']
        target = context.run_variation['target']

        target_path = f'./ease25-repl-pkg/code/control_group/{subject}'
                
        subject_command = self.subject_execution_templates[subject].format_map(defaultdict(str, {'target_path' : target_path,
                                                                                                 'target' : target,
                                                                                                 'python_venv' : self.python_venv_path,
                                                                                                }))

        self.external_run_dir = self.run_directory_template.format(results_output_path = self.results_output_path,
                                                                   name = self.name,
                                                                   run_directory_name = context.run_dir.name)

        self.energibrige_command = self.energibrige_command_template.format(metric_capturing_interval=self.metric_capturing_interval,
                                                                            run_command=subject_command,
                                                                            run_directory=self.external_run_dir)
        self.perf_command = self.perf_command_template.format(run_directory=self.external_run_dir)


        # Make directory of run on experimental machine
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f'sudo -S mkdir -p {self.external_run_dir}')
        del ssh

        output.console_log(f'Run directory on experimental machine: {self.external_run_dir}')
        output.console_log(f'Run command: {self.energibrige_command}')
        output.console_log_OK('Run configuration is successful.')

    def start_measurement(self, context: RunnerContext) -> None:
        output.console_log("Config.start_measurement() called!")    
        ssh = ExternalMachineAPI()
        wrapped_command = ssh.execute_remote_command(self.energibrige_command, arg=self.target_inputs[context.run_variation['target']],
                                   arg_from_file=True if isinstance(self.target_inputs[context.run_variation['target']], str) else False)
        output.console_log(f'Running energibridge with: {wrapped_command}')
        self.interaction_pid = int(ssh.stdout.readline())

        # Start perf monitor and attach it to the target process
        output.console_log(f'PID of run interaction: {self.interaction_pid}')
        perf_command = self.perf_command + str(self.interaction_pid)
        output.console_log(f'Running perf with: {perf_command}')
        ssh.execute_remote_command(perf_command, overwrite_channels=False)
        output.console_log_OK('Run has successfuly started.')

        # Energy Bridge Summary format: Energy consumption in joules: 7.630859375 for 2.0023594 sec of execution.
        next_line = ssh.stdout.readline()
        output.console_log(f'Summary of energibridge: {next_line}')
        parts = next_line.split()
        self.intermediary_results['total_joules'] = float(parts[4])
        self.intermediary_results['execution_time'] = float(parts[6])
        del ssh

        output.console_log_bold(f"Execution Time (seconds): {self.intermediary_results['execution_time']}")
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
        del ssh

        local_output_validation_file = f"./code/outputs/{context.run_variation['target']}.txt"
        received_output_file = f"{context.run_dir}/output.txt"
        # Check if run results are correct before storing data for the run
        if compare_files_bash(local_output_validation_file, received_output_file):
            # Extract perf output from experimental machine for current run
            perf_output = parse_perf_output(f"{context.run_dir}/perf.csv")
            energibridge_output = parse_energibridge_output(f"{context.run_dir}/energibridge.csv")
            return dict(perf_output.items() | self.intermediary_results.items() | energibridge_output.items())
        else:
            output.console_log_FAIL(f'Target function did not return the expected result.')
            return None

    def after_experiment(self) -> None:
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f'sudo -S rm -r ./ease25-repl-pkg/experiments')
        del ssh

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None