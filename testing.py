import paramiko
from dotenv import load_dotenv
from os import getenv
from scp import SCPClient
import subprocess

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

    def execute_remote_command(self, command : str, arg : str = None, arg_from_file : bool = False, overwrite_channels : bool = True):
        try:
            # Wrap command to fit paramiko call
            if arg_from_file:
                wrapped_command = f"{command}< <(echo {getenv('PASSWORD')} && cat {arg})" if command.startswith('sudo') else f'{command} <{arg}'
            if not arg_from_file:
                wrapped_command = f"echo {getenv('PASSWORD')} | {command} {arg}" if command.startswith('sudo') else f'{command} {arg}'
            # Execute the command
            if overwrite_channels:
                self.stdin, self.stdout, self.stderr = self.ssh.exec_command(wrapped_command)
            else:
                self.ssh.exec_command(wrapped_command)
        except paramiko.SSHException:
            print('Failed to send run command to machine!')
        except TimeoutError:
            print('Timeout reached while waiting for command output.')

    def copy_files_from_remote(self, remote_path, local_path):
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

def compare_files_bash(file1, file2):
    try:
        # Run the `diff` command to compare the files
        result = subprocess.run(["diff", file1, file2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout == b""  # True if no output, False otherwise
    except subprocess.CalledProcessError:
        return False  # Files are different or an error occurred 

sudo -S ./EnergiBridge/target/release/energibridge --interval 200 --summary --output ./energibridge.csv --command-output ./output.txt taskset -c 0 ./.venv/bin/python -c "import sys; sys.path.insert(0, './code/control_group/cython/build/'); import mandelbrot; mandelbrot.main(16000)"





        
