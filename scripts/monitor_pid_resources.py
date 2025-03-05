"""A Python script to monitor system resources for a given PID and optionally create 
a py-spy profiler report."""

import psutil
import pynvml
import time
import subprocess
import click
import threading
import csv


def total_cpu_percent_with_children(pid: int) -> float:
    """Return total CPU usage (%) for process `pid` and its children.

    Args:
        pid: Process ID to monitor.

    Returns:
        Total CPU usage (%) for the process and its children.
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return 0.0

    # Prime CPU measurement for child processes.
    processes = [parent] + parent.children(recursive=True)
    for proc in processes:
        try:
            proc.cpu_percent(interval=None)  # Prime the reading
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue  # Ignore inaccessible processes

    time.sleep(0.1)  # Allow measurements to update

    # Get the real CPU usage for all processes.
    total_cpu = 0.0
    for proc in processes:
        try:
            total_cpu += proc.cpu_percent(interval=0.0)  # Get real CPU %
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue  # Ignore processes that disappeared
    return total_cpu


def total_memory_with_children(pid: int) -> float:
    """Return total memory usage (MB) for a process and its children.

    Args:
        pid: Parent process ID.

    Returns:
        Total memory usage in MB.
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        all_processes = [parent] + children
        total_mem = 0
        for proc in all_processes:
            try:
                mem_info = proc.memory_info()
                total_mem += mem_info.rss  # Count physical memory (RAM)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue  # Ignore processes we can't access
        return total_mem / (1024 * 1024)  # Convert bytes to MB
    except psutil.NoSuchProcess:
        return 0.0  # Process not found


def total_gpu_usage_with_children(pid: int) -> tuple:
    """Return total GPU and VRAM usage (%) for process `pid` and its children.

    Args:
        pid: Process ID to monitor.

    Returns:
        Tuple containing total GPU usage (%) and total VRAM usage (MB) for the process
        and its children.
    """
    total_gpu_usage = 0
    total_vram_usage = 0

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        all_processes = [parent] + children

        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            for proc_info in processes:
                if proc_info.pid in [p.pid for p in all_processes]:
                    total_gpu_usage += pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    total_vram_usage += proc_info.usedGpuMemory / (1024 * 1024)  # MB
    except Exception:
        pass  # Ignore errors (e.g., no GPU available)
    return total_gpu_usage, total_vram_usage


def find_pid_by_name(name: str) -> int:
    """Find the PID of the process with the given name.

    Args:
        name: Name of the process to find.

    Returns:
        Process ID of the process with the given name.
    """
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if name in proc.info["cmdline"]:
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
def monitor_resources(
    pid: int,
    name: str,
    interval: int,
    duration: int,
    output: str,
    spy: bool,
    spy_output: str,
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
    """
    if pid == "auto":
        pid = find_pid_by_name(name)
        if pid is None:
            return
    else:
        pid = int(pid)

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
            cpu_usage = total_cpu_percent_with_children(pid)
            memory_usage = total_memory_with_children(pid)
            gpu_usage, vram_usage = total_gpu_usage_with_children(pid)

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
