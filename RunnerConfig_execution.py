from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, List, Any, Optional
from pathlib import Path
from os.path import dirname, realpath

# Experiment specific imports
import time
import paramiko
from os import getenv
from dotenv import load_dotenv
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
            output.console_log_FAIL('Failed to send run command to machine!')

    def execute_remote_command(self, command : str = '', overwrite_channels : bool = True):
        try:
            # Execute the command
            if overwrite_channels:
                self.stdin, self.stdout, self.stderr = self.ssh.exec_command(f"echo {getenv('PASSWORD')} | {command}" if command.startswith('sudo') else command)
            else:
                self.ssh.exec_command(f"echo {getenv('PASSWORD')} | {command}" if command.startswith('sudo') else command)
        except paramiko.SSHException:
            output.console_log_FAIL('Failed to send run command to machine!')
        except TimeoutError:
            output.console_log_FAIL('Timeout reached while waiting for command output.')

    def __del__(self):
        self.stdin.close()
        self.stdout.close()
        self.stderr.close()
        self.ssh.close()

def parse_perf_output(perf_output):
    # Initialize dictionary with all data_columns as keys and default to None
    perf_data = {
        'cache-references': None, 'cache-misses': None, 'LLC-loads': None, 'LLC-load-misses': None, 'LLC-stores': None, 'LLC-store-misses': None,
        'cache-references_percent': None, 'cache-misses_percent': None, 'LLC-loads_percent': None, 'LLC-load-misses_percent': None,
        'LLC-stores_percent': None, 'LLC-store-misses_percent': None
    }
    
    # Parse each line in the perf output
    for line in perf_output:
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

def parse_energibridge_output(energibridge_output):
    # Extract the header and rows from the data
    header = energibridge_output[0].strip().split(',')
    rows = [line.strip().split(',') for line in energibridge_output[1:]]
    
    # Initialize a dictionary to store sums and counts for each column
    totals = {col: 0.0 for col in header}
    counts = len(rows)  # Total number of data rows

    # Sum each column
    for row in rows:
        for i, value in enumerate(row):
            try:
                # Convert value to float and add to the respective total
                totals[header[i]] += float(value)
            except ValueError:
                # Skip if value is not a valid float
                continue

    # Calculate the average for each column and return as dictionary
    averages = {col: (totals[col] / counts) for col in header if counts > 0}
    return averages
    

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
    time_between_runs_in_ms:    int             = 1000 # 120000

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
            'python'    : '{python_venv} {target_path}/{target}.py {input}',
            'nuitka'    : '{target_path}/{target}.bin {input}',
            'pypy'      : None,
            'numba'     : None,
            'codon'     : None,
            'mypyc'     : None,
            'cython'    : None,
            'pyston'    : None,
            'pythran'   : None
        }

        self.targets_io = {
            'spectralnorm'      : {
                'input'                 : 5500,
                'expected_output'       : '1.274224153'
            },
            'binary-trees'      : {
                'input'                 : None,
                'expected_output'       : None
            },
            'fasta'             : {
                'input'                 : None,
                'expected_output'       : None
            },
            'k-nucleotide'      : {
                'input'                 : None,
                'expected_output'       : None
            },
            'n-body'            : {
                'input'                 : None,
                'expected_output'       : None
            },
            'mandelbrot'        : {
                'input'                 : None,
                'expected_output'       : None
            },
            'fannxkuch-redux'   : {
                'input'                 : None,
                'expected_output'       : None
            }
        }

        self.remote_path = "./ease25-repl-pkg"
        self.python_venv_path = f'{self.remote_path}/venv/bin/python'
        self.target_path_template = '{repository_path}/functions/{subject}/{target}'
        self.run_directory_template = '{repository_path}/experiments/{name}/{run_directory_name}'
        self.perf_output_file_template = '{run_directory}/perf.csv'
        self.energibridge_output_file_template = '{run_directory}/energibridge.csv'

        self.energibrige_command_template = 'sudo -S {repository_path}/EnergiBridge/target/release/energibridge --interval {metric_capturing_interval} --summary --output {energibridge_output_file} {run_command} & pid=$!; echo $pid'
        self.perf_command_template= 'sudo -S perf stat -x, -o {perf_output_file} -e cpu_core/cache-references/,cpu_core/cache-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/,cpu_core/LLC-stores/,cpu_core/LLC-store-misses/ -p '

        self.intermediary_results = {'total_joules' : None, 'execution_time' : None}
        self.run_result = None

        output.console_log("Custom config loaded")

    # TODO Update Runtable
    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("subject", ['python']) # 'numba', 'nuitka', 'pypy', 'codon', 'mypyc', 'cython', 'pyston', 'pythran'
        factor2 = FactorModel("target", ['spectralnorm']) # 'binary-trees', 'fasta', 'k-nucleotide', 'n-body', 'mandelbrot', 'fannxkuch-redux'
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            repetitions=10,
            exclude_variations=[],
            data_columns=['cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 'LLC-stores', 'LLC-store-misses',
                          'cache-references_percent', 'cache-misses_percent', 'LLC-loads_percent', 'LLC-load-misses_percent', 'LLC-stores_percent', 'LLC-store-misses_percent',
                          'CPU_USAGE_0', 'CPU_USAGE_1', 'CPU_USAGE_10', 'CPU_USAGE_11', 'CPU_USAGE_12', 'CPU_USAGE_13', 'CPU_USAGE_14', 'CPU_USAGE_15', 'CPU_USAGE_2', 'CPU_USAGE_3', 'CPU_USAGE_4', 'CPU_USAGE_5', 'CPU_USAGE_6', 'CPU_USAGE_7', 'CPU_USAGE_8', 'CPU_USAGE_9',
                          'DRAM_ENERGY (J)', 'PACKAGE_ENERGY (J)', 'PP0_ENERGY (J)', 'PP1_ENERGY (J)', 
                          'TOTAL_MEMORY', 'TOTAL_SWAP', 'USED_MEMORY', 'USED_SWAP',
                          'PROCESS_CPU_USAGE', 'PROCESS_MEMORY', 'PROCESS_VIRTUAL_MEMORY',
                          'total_joules', 'execution_time']
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        output.console_log("Config.before_experiment() called!")
        # # Warmup machine for one minute
        # ssh = ExternalMachineAPI()
        # warmup_command = f'{self.python_venv_path} {self.remote_path}/functions/warmup.py 1000 & pid=$!; echo $pid'
        # ssh.execute_remote_command(warmup_command)
        # time.sleep(self.warmup_time)
        # ssh.execute_remote_command(f'kill {ssh.stdout.readline()}')

        # # Cooldown machine
        # time.sleep(self.post_warmup_cooldown_time)

        output.console_log_OK("Warmup finished. Experiment is starting now!")

    def before_run(self) -> None:
        pass

    def start_run(self, context: RunnerContext) -> None:
        output.console_log("Config.start_run() called!")

        subject = context.run_variation['subject']
        target = context.run_variation['target']
        
        target_path = self.target_path_template.format(subject=subject, 
                                                       target=target,
                                                       repository_path=self.remote_path)
        
        subject_command = self.subject_execution_templates[subject].format_map(defaultdict(str, {'target_path' : target_path,
                                                                                                 'target' : target,
                                                                                                 'python_venv' : self.python_venv_path,
                                                                                                 'input' : self.targets_io[target]['input']}))

        self.run_dir = self.run_directory_template.format(results_output_path = self.results_output_path,
                                                          name = self.name, 
                                                          run_directory_name = context.run_dir.name,
                                                          repository_path=self.remote_path)
        
        self.perf_output_file = self.perf_output_file_template.format(run_directory=self.run_dir)
        self.energibridge_output_file = self.energibridge_output_file_template.format(run_directory=self.run_dir)

        self.energibrige_command = self.energibrige_command_template.format(metric_capturing_interval=self.metric_capturing_interval,
                                                                            energibridge_output_file=self.energibridge_output_file,
                                                                            run_command=subject_command,
                                                                            repository_path=self.remote_path)
        self.perf_command = self.perf_command_template.format(perf_output_file=self.perf_output_file)


        # Make directory of run on experimental machine
        ssh = ExternalMachineAPI()
        ssh.execute_remote_command(f'sudo -S mkdir -p {self.run_dir}')
        del ssh

        output.console_log(f'Run directory on experimental machine: {self.run_dir}')
        output.console_log(f'Run command: {self.energibrige_command}')
        output.console_log_OK('Run configuration is successful.')

    def start_measurement(self, context: RunnerContext) -> None:
        output.console_log("Config.start_measurement() called!")    
        ssh = ExternalMachineAPI()    
        ssh.execute_remote_command(self.energibrige_command)
        output.console_log(f'Running energibridge with: {self.energibrige_command}')
        self.interaction_pid = int(ssh.stdout.readline())

        # Start perf monitor and attach it to the target process
        output.console_log(f'PID of run interaction: {self.interaction_pid}')
        perf_command = self.perf_command + str(self.interaction_pid)
        output.console_log(f'Running perf with: {perf_command}')
        ssh.execute_remote_command(perf_command, overwrite_channels=False)
        output.console_log_OK('Run has successfuly started.')
        
        # Read Output of the energibridge command
        # Result of the command
        self.run_result = ssh.stdout.readline()
        output.console_log(f"Output of command: {self.run_result}")

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

        # Check if run_result is correct before storing data for the run
        if self.run_result.strip() == self.targets_io[context.run_variation['target']]['expected_output']:
            # Extract perf output from experimental machine for current run
            ssh = ExternalMachineAPI()
            ssh.execute_remote_command(f'cat {self.perf_output_file}')
            perf_data = ssh.stdout.readlines()
            perf_output = parse_perf_output(perf_data[2:])

            # TODO Save energibridge data averages
            ssh.execute_remote_command(f'cat {self.energibridge_output_file}')
            energibridge_data = ssh.stdout.readlines()
            energibridge_output = parse_energibridge_output(energibridge_data[1:])
            
            del ssh
            return dict(perf_output.items()  | self.intermediary_results.items()) | energibridge_output.items()
        else:
            output.console_log_FAIL(f'Unexpected command result:\nExpected: {self.targets_io[context.run_variation['target']]['expected_output']}\nReceived: {self.run_result.strip()}')
            return None

    def after_experiment(self) -> None:
        # ssh = ExternalMachineAPI()
        # ssh.execute_remote_command(f'sudo -S rm -r {self.remote_path}/experiments')
        # del ssh
        pass

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None