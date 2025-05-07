# ComfyUI Helper Scripts

This directory contains helper scripts to simplify the deployment and management of **ComfyStream**:

- **Ansible Playbook (`ansible/plays/setup_comfystream.yml`)** – Deploys ComfyStream on any cloud provider.  
- `monitor_pid_resources.py`: Monitors and profiles the resource usage of a running ComfyStream server.

## Usage Instructions

### Ansible Playbook (Cloud-Agnostic Deployment)

This repository provides an [Ansible playbook](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html) to streamline the deployment of **ComfyStream** across any cloud provider. For comprehensive setup instructions, see the Ansible section in the [ComfyStream Installation Guide](https://docs.comfystream.org/technical/get-started/install#deploy-with-ansible).

### Profiling a Running ComfyStream Server

To monitor the resource consumption of a running ComfyStream server, use the `monitor_pid_resources.py` script:

1. **Start the ComfyStream server** and execute a streaming workflow.
2. **Run the profiling script**:

   ```bash
   python monitor_pid_resources.py --name app.py
   ```

   The script will automatically try to find the process ID (PID) of the server. If you prefer to specify the PID manually, you can retrieve it using:

   ```bash
   pgrep -f app.py | xargs ps -o pid,cmd --pid
   ```

   Then run the profiling script with the retrieved PID:

   ```bash
   python monitor_pid_resources.py --pid <PID>
   ```

3. **Running Inside a Container**: If you are running the script inside a container, use the `--host-pid` option to provide the host PID for accurate GPU monitoring:

   ```bash
   python monitor_pid_resources.py --name app.py --host-pid <HOST_PID>
   ```

   Find `<HOST_PID>` with `nvidia-smi` on the host.

The script will continuously track **CPU and memory usage** at specified intervals. If the `--spy` flag is used, it will also generate a **detailed Py-Spy profiler report** for deeper performance insights.

### Additional Options

For a complete list of available options, run:

```bash
python monitor_pid_resources.py --help
```
