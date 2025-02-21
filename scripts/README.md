# ComfyUI Helper Scripts

This directory contains various helper scripts designed to streamline working with ComfyStream:

- `monitor_pid_resources.py`: Monitors and profiles the resource usage of a running ComfyStream server.

## Usage Instructions

### Profiling a Running ComfyStream Server

To monitor the resource consumption of a running ComfyStream server, use the `monitor_pid_resources.py` script:

1. **Start the ComfyStream server** and execute a streaming workflow.
2. **Retrieve the process ID (PID) of the server** using:

   ```bash
   ps aux | grep app.py
   ```

3. **Run the profiling script:**

   ```bash
   python monitor_pid_resources.py --pid <PID>
   ```

The script will continuously track **CPU and memory usage** at specified intervals. If the `--spy` flag is used, it will also generate a **detailed Py-Spy profiler report** for deeper performance insights.

### Additional Options

For a complete list of available options, run:

```bash
python monitor_pid_resources.py --help
```
