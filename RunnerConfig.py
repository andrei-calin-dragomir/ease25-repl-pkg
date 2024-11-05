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
from os import getenv
from dotenv import load_dotenv

load_dotenv()

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


        self.interaction_pid = None
        self.perf_monitor = None

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("subject", ['python', 'nuitka']) # 'pypy', 'numba', 'codon', 
        factor2 = FactorModel("target", ['spectralnorm'])
        self.run_table_model = RunTableModel(
            factors=[factor1, factor2],
            repetitions=10,
            exclude_variations=[],
            data_columns=['cache-references', 'cache-misses', 'LLC-loads', 'LLC-load-misses', 'LLC-stores', 'LLC-store-misses',
                          'cache-references_percent', 'cache-misses_percent', 'LLC-loads_percent', 'LLC-load-misses_percent', 'LLC-stores_percent', 'LLC-store-misses_percent',
                          'avg_cpu', 'avg_mem', 'execution_time']
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        """Perform any activity required before starting the experiment here
        Invoked only once during the lifetime of the program."""
        # Make directory for current experiment on experimental machine
        # execute_remote_command(f'mkdir -p experiments/{self.name}')

        output.console_log("Config.before_experiment() called!")

    def before_run(self) -> None:
        """Perform any activity required before starting a run.
        No context is available here as the run is not yet active (BEFORE RUN)"""
        output.console_log("Config.before_run() called!")

    def start_run(self, context: RunnerContext) -> None:
        """Perform any activity required for starting the run here.
        For example, starting the target system to measure.
        Activities after starting the run should also be performed here."""
        output.console_log("Config.start_run() called!")
        
        subject_command = self.subject_execution_templates[context.run_variation['subject']]
        target_path = self.target_path_template.format(subject=context.run_variation['subject'], target=context.run_variation['target'])

        run_command = subject_command.format(target_path=target_path, target=context.run_variation['target'])
        output.console_log_bold(f'Run command: {run_command}')
            
        # Load the command and suspend it but return the PID so that monitors can attach to it.
        # self.interaction_pid = execute_remote_command(f"bash -c \'{run_command}\' & pid=$!; kill -SIGSTOP $pid; echo $pid")
        output.console_log_bold(f'Interaction_PID: {self.interaction_pid}')
        
        output.console_log_OK(f'Spawned and suspended process on remote.')

    def start_measurement(self, context: RunnerContext) -> None:
        """Perform any activity required for starting measurements."""
        output.console_log("Config.start_measurement() called!")

        # Create run measurement directory
        run_dir = f'experiments/{self.name}/{context.run_dir.name}/'
        # execute_remote_command(f'mkdir -p {run_dir}')
        output.console_log(run_dir)
        
        perf_command_template = 'echo {password} | bash -c \'sudo -S perf stat -x, -o {run_dir}perf.csv -e cpu_core/cache-references/,cpu_core/cache-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/,cpu_core/LLC-stores/,cpu_core/LLC-store-misses/ -p {process_id}\''

        # Start perf monitor and attach it to the target process
        # execute_remote_command(perf_command_template.format(password=getenv('PASSWORD'),
        #                                                     run_dir=run_dir,
        #                                                     process_id=self.interaction_pid))

        output.console_log_OK('Monitors are ready to collect.')
        time.sleep(1)  # Allow time for monitoring tools to attach

    def interact(self, context: RunnerContext) -> None:
        """Perform any interaction with the running target system here, or block here until the target finishes."""
        output.console_log("Config.interact() called!")

        self.execution_time = time.time()
        # Resume interaction process once all monitors are ready
        # execute_remote_command(f"kill -SIGCONT {self.interaction_pid}")
        self.execution_time = (time.time() - self.execution_time) * 1000 # Convert to milliseconds
        
        output.console_log_OK('Run command finished successfully.')

    def stop_measurement(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping measurements."""
        output.console_log("Config.stop_measurement called!")

        # No need to stop perf as it dies with the interaction process

    def stop_run(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping the run.
        Activities after stopping the run should also be performed here."""
        self.interaction_pid = None
        output.console_log("Config.stop_run() called!")

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """Parse and process any measurement data here.
        You can also store the raw measurement data under `context.run_dir`
        Returns a dictionary with keys `self.run_table_model.data_columns` and their values populated"""
        output.console_log("Config.populate_run_data() called!")

        perf_file = f'experiments/{self.name}/{context.run_dir.name}/perf.csv'

        # Extract perf output from experimental machine for current run
        # perf_data = execute_remote_command(f'cat {perf_file}')
        
        # Package the received data
        # perf_output = parse_perf_output(perf_data[2:])
        perf_output = {}

        auxiliary_data = {
            'execution_time' : self.execution_time
        }

        return dict(perf_output.items() | auxiliary_data.items())

    def after_experiment(self) -> None:
        """Perform any activity required after stopping the experiment here
        Invoked only once during the lifetime of the program."""

        output.console_log("Config.after_experiment() called!")

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None