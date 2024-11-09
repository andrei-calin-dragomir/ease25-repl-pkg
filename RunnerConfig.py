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
import paramiko
from os import getenv
from dotenv import load_dotenv

class ExternalMachineAPI:
    def __init__(self):
        load_dotenv()

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.ssh.connect(hostname=getenv('HOSTNAME'), username=getenv('USERNAME'), password=getenv('PASSWORD'))
        except paramiko.SSHException:
            output.console_log_FAIL('Failed to send run command to machine!')

    def execute_remote_command(self, command : str = ''):
        try:
            # Execute the command
            self.stdin, self.stdout, self.stderr = self.ssh.exec_command(f'echo {getenv('PASSWORD')} | {command}' if command.startswith('sudo') else command)
        except paramiko.SSHException:
            output.console_log_FAIL('Failed to send run command to machine!')
        except TimeoutError:
            output.console_log_FAIL('Timeout reached while waiting for command output.')

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

def parse_energi_output(perf_output):
    return {}
    

class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))

    # ================================ USER SPECIFIC CONFIG ================================
    """The name of the experiment."""
    name:                       str             = "python_experiment"

    """The path in which Experiment Runner will create a folder with the name `self.name`, in order to store the
    results from this experiment. (Path does not need to exist - it will be created if necessary.)
    Output path defaults to the config file's path, inside the folder 'experiments'"""
    results_output_path:        Path            = ROOT_DIR / 'experiments'

    """Experiment operation type. Unless you manually want to initiate each run, use `OperationType.AUTO`."""
    operation_type:             OperationType   = OperationType.AUTO

    """The time Experiment Runner will wait after a run completes.
    This can be essential to accommodate for cooldown periods on some systems."""
    time_between_runs_in_ms:    int             = 5000

    # Dynamic configurations can be one-time satisfied here before the program takes the config as-is
    # e.g. Setting some variable based on some criteria
    def __init__(self):
        """Executes immediately after program start, on config load"""

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

        load_dotenv()

        self.run_table_model = None  # Initialized later
        
        
        self.subject_compilation_templates = {
            'python': '',
            'nuitka': './venv/bin/python -m nuitka {target_path}/{target}.py --output-dir={target_path}',
            'pypy': '',
            'numba': '',
            'codon': ''
        }

        self.subject_execution_templates = {
            'python': './venv/bin/python {target_path}/{target}.py 1000',
            'nuitka': '{target_path}/{target}.bin 1000',
            'pypy': '',
            'numba': '',
            'codon': ''
        }

        self.target_path_template = './functions/{subject}/{target}'
        self.perf_output_file_template = '{self.run_dir}/perf.csv'
        self.energibridge_output_file_template = '{run_directory}/energibridge.csv'
        self.run_command_template = 'bash -c {subject_command} &'
        self.run_directory_template = '{results_output_path}/{name}/{run_directory_name}'

        self.energibrige_command_template = 'sudo -S ./EnergiBridge/target/release/energibridge --interval {metric_capturing_interval} --summary --output {energibridge_output_file} {run_command}'
        self.perf_command_template= 'sudo -S perf stat -x, -o {perf_output_file} -e cpu_core/cache-references/,cpu_core/cache-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/,cpu_core/LLC-stores/,cpu_core/LLC-store-misses/ -p {interaction_pid}'

        self.interaction_pid = None
        self.perf_monitor = None

        self.machine = ExternalMachineAPI()

        """The frequency at which the metric collectors will collect data (in miliseconds)."""
        self.metric_capturing_interval: int = 1000

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        # TODO Update Factors
        factor1 = FactorModel("subject", ['python', 'nuitka']) # 'pypy', 'numba', 'codon', 
        factor2 = FactorModel("target", ['spectralnorm'])
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            repetitions=10,
            exclude_variations=[],
            data_columns=['cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 'LLC-stores', 'LLC-store-misses',
                          'cache-references_percent', 'cache-misses_percent', 'LLC-loads_percent', 'LLC-load-misses_percent', 'LLC-stores_percent', 'LLC-store-misses_percent',
                          'total_joules',
                          'avg_cpu', 'avg_mem', 'execution_time']
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        pass

    def before_run(self) -> None:
        """Perform any activity required before starting a run.
        No context is available here as the run is not yet active (BEFORE RUN)"""
        output.console_log("Config.before_run() called!")

        # TODO Warmup machine check CHECKLIST


    def start_run(self, context: RunnerContext) -> None:
        """Perform any activity required for starting the run here.
        For example, starting the target system to measure.
        Activities after starting the run should also be performed here."""
        output.console_log("Config.start_run() called!")
        
        target_path = self.target_path_template.format(subject=context.run_variation['subject'], 
                                                       target=context.run_variation['target'])
        subject_command = self.subject_execution_templates[context.run_variation['subject']].format(target_path=target_path, 
                                                                                                    target=context.run_variation['target'])

        self.perf_output_file = self.perf_output_file_template.format(run_directory=self.run_dir)
        self.energibridge_output_file = self.energibridge_output_file_template.format(run_directory=self.run_dir)

        self.energibrige_command = self.energibrige_command_template.format(metric_capturing_interval=self.metric_capturing_interval,
                                                                            energibridge_output_file=self.energibridge_output_file,
                                                                            run_command=self.run_command)
        self.perf_command = self.perf_command_template.format(perf_output_file=self.perf_output_file, 
                                                              interaction_pid=self.interaction_pid)

        self.run_command = self.run_command_template.format(subject_command=subject_command)
        self.run_dir = self.run_directory_template.format(results_output_path = self.results_output_path,
                                                          name = self.name, 
                                                          run_directory_name = context.run_dir.name)

        # Make directory of run on experimental machine
        self.machine.execute_remote_command(f'sudo mkdir -p {self.run_dir}')

        output.console_log_bold(f'Run directory on experimental machine: {self.run_dir}')
        output.console_log_bold(f'Run command: {self.run_command}')
        output.console_log_OK('Run configuration is successful.')

    def start_measurement(self, context: RunnerContext) -> None:
        """Perform any activity required for starting measurements."""
        output.console_log("Config.start_measurement() called!")        
        self.machine.execute_remote_command(self.energibrige_command)

        # Output format '[<process_count>] <PID>' -> PID
        self.interaction_pid = self.machine.stdout.readline().split()[-1]
        output.console_log_bold(f'PID of run interaction: {self.interaction_pid}')

        # Start perf monitor and attach it to the target process
        print(self.perf_command)
        self.machine.execute_remote_command(self.perf_command)
        print(self.perf_command)
        output.console_log_OK('Run has successfuly started.')

    def interact(self, context: RunnerContext) -> None:
        pass

    def stop_measurement(self, context: RunnerContext) -> None:
        
        # Output of the energibridge command
        # Energy consumption in joules: 7.630859375 for 2.0023594 sec of execution.
        parts = self.machine.stdout.readline().split()
        self.total_joules = float(parts[4])
        self.execution_time = float(parts[7])
        output.console_log_bold(f'Execution Time (seconds): {self.execution_time}')
        output.console_log_OK('Run has successfuly finished.')

    def stop_run(self, context: RunnerContext) -> None:
        pass

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """Parse and process any measurement data here.
        You can also store the raw measurement data under `context.run_dir`
        Returns a dictionary with keys `self.run_table_model.data_columns` and their values populated"""
        output.console_log("Config.populate_run_data() called!")

        # Extract perf output from experimental machine for current run
        self.machine.execute_remote_command(f'cat {self.perf_output_file}')
        print(self.machine.stdout.readlines())
        # perf_output = parse_perf_output(self.machine.stdout.readlines()[2:])

        auxiliary_data = {
            'execution_time' : self.execution_time,
            'total_joules' : self.total_joules
        }

        # TODO Save energibridge data averages
        self.machine.execute_remote_command(f'cat {self.energibridge_output_file}')
        print(self.machine.stdout.readlines())
        # energibridge_output = parse_energi_output(self.machine.stdout.readlines())

        # return dict(perf_output.items() | energibridge_output.items() | auxiliary_data.items())

    def after_experiment(self) -> None:
        self.machine.ssh.close()

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None