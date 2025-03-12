"""A Python script to monitor system resources for a given PID and optionally create
a py-spy profiler report."""

import psutil
import pynvml
import time
import subprocess
import click
import threading
import csv
from pathlib import Path
from typing import List


def is_running_inside_container():
    """Detects if the script is running inside a container."""
    if Path("/.dockerenv").exists():
        return True
    try:
        with open("/proc/1/cgroup", "rt") as f:
            return any("docker" in line or "kubepods" in line for line in f)
    except FileNotFoundError:
        return False


def get_all_processes(pid: int) -> List[psutil.Process]:
    """Return the parent process and all its children.

    Args:
        pid: Parent process ID.

    Returns:
        List of all processes (parent and children).
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        return [parent] + children
    except psutil.NoSuchProcess:
        return []


def total_cpu_percent(pids: List[psutil.Process]) -> float:
    """Return total CPU usage (%) for a list of process IDs.
    Args:
        pids: List of process IDs to monitor.

    Returns:
        Total CPU usage (%) for the process IDs.
    """
    if not pids:
        return 0.0

    # Prime CPU measurement for child processes.
    for proc in pids:
        try:
            proc.cpu_percent(interval=None)  # Prime the reading
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue  # Ignore inaccessible processes

    time.sleep(0.1)  # Allow measurements to update

    # Get the real CPU usage for all processes.
    total_cpu = 0.0
    for proc in pids:
        try:
            total_cpu += proc.cpu_percent(interval=0.0)  # Get real CPU %
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue  # Ignore processes that disappeared
    return total_cpu


def total_memory(pids: List[psutil.Process]) -> float:
    """Return total memory usage (MB) for a list of process IDs.

    Args:
        pids: List of process IDs to monitor.

    Returns:
        Total memory usage in MB for the process IDs.
    """
    if not pids:
        return 0.0

    total_mem = 0
    for proc in pids:
        try:
            mem_info = proc.memory_info()
            total_mem += mem_info.rss  # Count physical memory (RAM)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue  # Ignore processes we can't access
    return total_mem / (1024 * 1024)  # Convert bytes to MB


def total_gpu_usage(pids: List[int]) -> tuple:
    """Return total GPU and VRAM usage (%) for a list of process IDs.

    Args:
        pids: List of process IDs to monitor.

    Returns:
        Tuple containing total GPU usage (%) and total VRAM usage (MB) for the
        proccess IDs.
    """
    total_usage = 0
    total_vram_usage = 0

    try:
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            for proc_info in processes:
                if proc_info.pid in pids:
                    total_usage += pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    total_vram_usage += proc_info.usedGpuMemory / (1024 * 1024)  # MB
    except Exception:
        pass  # Ignore errors (e.g., no GPU available)
    return total_usage, total_vram_usage


def find_pid_by_name(name: str) -> int:
    """Find the PID of the process with the given name.

    Args:
        name: Name of the process to find.

    Returns:
        Process ID of the process with the given name.
    """
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if proc.info["cmdline"] and name in proc.info["cmdline"]:
            found_pid = proc.info["pid"]
            click.echo(
                click.style(f"Found process '{name}' with PID {found_pid}.", fg="green")
            )
            return found_pid
    click.echo(click.style(f"Error: Process with name '{name}' not found.", fg="red"))
    return None


@click.command()
@click.option(
    "--pid", type=str, default="auto", help='Process ID or "auto" to find by name'
)
@click.option(
    "--name", type=str, default="app.py", help="Process name (default: app.py)"
)
@click.option("--interval", type=int, default=2, help="Monitoring interval (seconds)")
@click.option(
    "--duration", type=int, default=30, help="Total monitoring duration (seconds)"
)
@click.option("--output", type=str, default=None, help="File to save logs (optional)")
@click.option("--spy", is_flag=True, help="Enable py-spy profiling")
@click.option(
    "--spy-output", type=str, default="pyspy_profile.svg", help="Py-Spy output file"
)
@click.option(
    "--host-pid",
    type=int,
    default=None,
    help="Host PID for GPU monitoring when running inside a container. Use 'pgrep -f app.py' to find the PID.",
)
def monitor_resources(
    pid: int,
    name: str,
    interval: int,
    duration: int,
    output: str,
    spy: bool,
    spy_output: str,
    host_pid: int,
):
    """Monitor system resources for a given PID and optionally create a py-spy profiler
    report.

    Args:
        pid (int): Process ID of the Python script.
        name (str): Name of the Python script.
        interval (int): Monitoring interval in seconds.
        duration (int): Total monitoring duration in seconds.
        output (str): File to save logs (optional).
        spy (bool): Enable py-spy profiling.
        spy_output (str): Py-Spy output file.
        host_pid (int): Host PID for GPU monitoring (useful inside containers).
    """
    if pid == "auto":
        pid = find_pid_by_name(name)
        if pid is None:
            return
    else:
        pid = int(pid)

    if is_running_inside_container():
        if not host_pid:
            click.echo(
                click.style(
                    "Warning: Running inside a container. GPU monitoring may not work correctly "
                    "since `nvidia-smi` uses the host PID namespace. To fix this, provide the "
                    "host PID using the `--host-pid` flag.",
                    fg="yellow",
                )
            )
        else:
            click.echo(
                click.style(
                    f"Running inside a container. Monitoring GPU using host PID {host_pid}.",
                    fg="cyan",
                )
            )

    if not psutil.pid_exists(pid):
        click.echo(click.style(f"Error: Process with PID {pid} not found.", fg="red"))
        return

    click.echo(
        click.style(f"Monitoring PID {pid} for {duration} seconds...", fg="green")
    )

    def run_py_spy():
        """Run py-spy profiler for deep profiling."""
        click.echo(click.style("Running py-spy for deep profiling...", fg="green"))
        spy_cmd = f"py-spy record -o {spy_output} --pid {pid} --duration {duration}"
        try:
            subprocess.run(
                spy_cmd, shell=True, check=True, capture_output=True, text=True
            )
            click.echo(
                click.style(f"Py-Spy flame graph saved to {spy_output}", fg="green")
            )
        except subprocess.CalledProcessError as e:
            click.echo(click.style(f"Error running py-spy: {e.stderr}", fg="red"))

    # Start py-spy profiling in a separate thread if enabled.
    if spy:
        spy_thread = threading.Thread(target=run_py_spy)
        spy_thread.start()

    # Start main resources monitoring loop.
    pynvml.nvmlInit()
    monitor_start_time = time.time()
    end_time = time.time() + duration
    logs = []
    cpu_usages, ram_usages, gpu_usages, vram_usages = [], [], [], []
    while time.time() < end_time:
        start_time = time.time()
        elapsed_monitor_time = time.time() - monitor_start_time
        progress = (elapsed_monitor_time / duration) * 100
        try:
            all_processes = get_all_processes(pid)
            cpu_usage = total_cpu_percent(all_processes)
            memory_usage = total_memory(all_processes)
            gpu_usage, vram_usage = total_gpu_usage(
                [proc.pid for proc in all_processes] if not host_pid else [host_pid]
            )

            log_entry = {
                "CPU (%)": cpu_usage,
                "RAM (MB)": memory_usage,
                "GPU (%)": gpu_usage,
                "VRAM (MB)": vram_usage,
            }
            click.echo(
                f"[{progress:.1f}%] CPU: {cpu_usage:.2f}%, RAM: {memory_usage:.2f}MB, "
                f"GPU: {gpu_usage:.2f}%, VRAM: {vram_usage:.2f}MB"
            )
            logs.append(log_entry)
            cpu_usages.append(cpu_usage)
            ram_usages.append(memory_usage)
            gpu_usages.append(gpu_usage)
            vram_usages.append(vram_usage)

            # Adjust sleep time to maintain exact interval
            elapsed_time = time.time() - start_time
            sleep_time = max(0, interval - elapsed_time)
            time.sleep(sleep_time)
        except psutil.NoSuchProcess:
            click.echo(click.style("Error: Process terminated!", fg="red"))
            break

    pynvml.nvmlShutdown()

    # Calculate and log averages
    avg_cpu = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
    avg_ram = sum(ram_usages) / len(ram_usages) if ram_usages else 0
    avg_gpu = sum(gpu_usages) / len(gpu_usages) if gpu_usages else 0
    avg_vram = sum(vram_usages) / len(vram_usages) if vram_usages else 0

    click.echo(
        f"AVERAGE - CPU: {avg_cpu:.2f}%, RAM: {avg_ram:.2f}MB, GPU: {avg_gpu:.2f}%, VRAM: {avg_vram:.2f}MB"
    )

    # Save logs if output file is provided.
    if output:
        with open(output, "w", newline="") as csvfile:
            fieldnames = ["CPU (%)", "RAM (MB)", "GPU (%)", "VRAM (MB)"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(logs)
        click.echo(click.style(f"Logs saved to {output}", fg="green"))

    # Wait for py-spy thread to finish if it was started.
    if spy:
        spy_thread.join()


if __name__ == "__main__":
    monitor_resources()
