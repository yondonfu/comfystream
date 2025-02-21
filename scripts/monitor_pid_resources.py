"""A Python script to monitor system resources for a given PID and optionally create 
a py-spy profiler report."""

import psutil
import pynvml
import time
import subprocess
import click
import threading
import csv


@click.command()
@click.option("--pid", type=int, required=True, help="Process ID of the Python script")
@click.option("--interval", type=int, default=2, help="Monitoring interval (seconds)")
@click.option(
    "--duration", type=int, default=30, help="Total monitoring duration (seconds)"
)
@click.option(
    "--output",
    type=str,
    default=None,
    help="File to save system resource logs (optional)",
)
@click.option("--spy", is_flag=True, help="Enable py-spy profiling")
@click.option(
    "--spy-output", type=str, default="pyspy_profile.svg", help="Py-Spy output file"
)
def monitor_resources(
    pid: int, interval: int, duration: int, output: str, spy: bool, spy_output: str
):
    """Monitor system resources for a given PID and optionally create a py-spy profiler
    report.

    Args:
        pid (int): Process ID of the Python script.
        interval (int): Monitoring interval in seconds.
        duration (int): Total monitoring duration in seconds.
        output (str): File to save logs (optional).
        spy (bool): Enable py-spy profiling.
        spy_output (str): Py-Spy output file.
    """
    if not psutil.pid_exists(pid):
        click.echo(click.style(f"Error: Process with PID {pid} not found.", fg="red"))
        return

    click.echo(
        click.style(
            f"Monitoring system resources for PID {pid} for {duration} seconds...",
            fg="green",
        )
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
    end_time = time.time() + duration
    logs = []
    cpu_usages, ram_usages, gpu_usages, vram_usages = [], [], [], []
    while time.time() < end_time:
        try:
            # General system usage.
            process = psutil.Process(pid)
            cpu_usage = process.cpu_percent(interval=interval)
            ram_usage = process.memory_info().rss / (1024 * 1024)  # MB

            # GPU usage.
            process_gpu_usage = 0
            process_vram_usage = 0
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                for proc_info in processes:
                    if proc_info.pid == pid:
                        process_gpu_usage = pynvml.nvmlDeviceGetUtilizationRates(
                            handle
                        ).gpu
                        process_vram_usage = proc_info.usedGpuMemory / (
                            1024 * 1024
                        )  # MB
                        break

            # Collect and log resource usage.
            log_entry = {
                "CPU (%)": cpu_usage,
                "RAM (MB)": ram_usage,
                "GPU (%)": process_gpu_usage,
                "VRAM (MB)": process_vram_usage,
            }
            click.echo(
                f"CPU: {cpu_usage:.2f}%, RAM: {ram_usage:.2f}MB, GPU: {process_gpu_usage:.2f}%, VRAM: {process_vram_usage:.2f}MB"
            )
            logs.append(log_entry)
            cpu_usages.append(cpu_usage)
            ram_usages.append(ram_usage)
            gpu_usages.append(process_gpu_usage)
            vram_usages.append(process_vram_usage)
        except psutil.NoSuchProcess:
            click.echo(click.style("Error: Process terminated!"))
            break

    pynvml.nvmlShutdown()

    # Calculate and log average resource usage.
    avg_cpu_usage = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
    avg_ram_usage = sum(ram_usages) / len(ram_usages) if ram_usages else 0
    avg_gpu_usage = sum(gpu_usages) / len(gpu_usages) if gpu_usages else 0
    avg_vram_usage = sum(vram_usages) / len(vram_usages) if vram_usages else 0
    avg_log_entry = {
        "CPU (%)": avg_cpu_usage,
        "RAM (MB)": avg_ram_usage,
        "GPU (%)": avg_gpu_usage,
        "VRAM (MB)": avg_vram_usage,
    }
    click.echo(
        f"AVERAGE - CPU: {avg_cpu_usage:.2f}%, RAM: {avg_ram_usage:.2f}MB, GPU: {avg_gpu_usage:.2f}%, VRAM: {avg_vram_usage:.2f}MB"
    )
    logs.append(avg_log_entry)

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
