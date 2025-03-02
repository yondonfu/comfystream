# ComfyUI Helper Scripts

This directory contains various helper scripts designed to streamline working with ComfyStream:

- `spinup_comfystream_tensordock.py`: Automates the setup of a ComfyStream instance on a [Tensordock server](https://tensordock.com/), installs dependencies and starts the server.
- **Ansible Playbook (`ansible/plays/setup_comfystream.yml`)**: Provides a manual alternative for setting up ComfyStream on any cloud provider.

## Usage Instructions

### TensorDock Auto-Setup (Fully Automated)

The `spinup_comfystream_tensordock.py` script automates the entire process of setting up a ComfyStream instance on a [TensorDock server](https://tensordock.com/). To use this script, follow these steps:

1. **Create a Tensordock Account**: Register at [Tensordock](https://dashboard.tensordock.com/register), attach a credit card, and create an API key and token.
2. **Set Up a Python Virtual Environment**:
   Create and activate a virtual environment using [Conda](https://docs.anaconda.com/miniconda/) and install the required dependencies:

    ```bash
    conda create -n comfystream python=3.8
    conda activate comfystream
    pip install -r requirements.txt
    ```

3. **Check Available Script Options** *(Optional but Recommended)*:  
   To view available options, run:

    ```bash
    python spinup_comfystream_tensordock.py --help
    ```

4. **Run the Script**:  
   Execute the following command to spin up a ComfyStream instance:

    ```bash
    python spinup_comfystream_tensordock.py --api-key <API_KEY> --api-token <API_TOKEN>
    ```

5. **Access the Server**:  
   The script will create the instance, install dependencies, and start the server. Once completed, you can access ComfyStream using the provided URLs.

6. **Stop the Server** *(When No Longer Needed)*:
   Run the following command to delete the instance:

    ```bash
    python spinup_comfystream_tensordock.py --delete <VM_ID>
    ```

   Replace`<VM_ID>` with the ID of the VM (found in script logs or the [Tensordock dashboard](https://dashboard.tensordock.com/).

> [!WARNING]
> If you encounter max retries exceeded with url errors, the VM might have been created but is inaccessible. Check the [TensorDock dashboard](https://dashboard.tensordock.com/instances), delete the WM, wait 2-3 minutes, then rerun the script.

### Cloud-Agnostic Automated Setup (Ansible-Based Deployment)

For users who prefer to deploy on any cloud provider, an [Ansible playbook](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html) is available. This method automates the ComfyStream installation but requires manual VM provisioning.

1. **Create a VM**:  
   Deploy a VM on your preferred cloud provider (e.g., [Tensordock](https://marketplace.tensordock.com/deploy?gpu=geforcertx4090-pcie-24gb&gpuCount=1&ramAmount=16&vcpuCount=4&storage=100&os=Ubuntu-22.04-LTS), AWS, Google Cloud, Azure). The VM should meet the following minimum requirements:
   - **GPU**: 20GB VRAM
   - **RAM**: 16GB
   - **CPU**: 4 vCPUs
   - **Storage**: 100GB

2. **Open Ports**:  
   Ensure that the following ports are open **inbound and outbound** on your VM's firewall/security group:  
   - **SSH (Port 22)** – Required for remote SSH access  
   - **HTTPS (Port 8189)** – Used for ComfyUI/ComfyStream access  
  
3. **Install Ansible**:  
   Follow the [Ansible installation guide](https://docs.ansible.com/ansible/latest/installation_guide/index.html) to install Ansible on your local machine.

4. **Configure the Inventory File**:  
   Add the VM's public IP address to [ansible/inventory.yml](ansible/inventory.yml).

5. **Run the Playbook**:  
   Execute the following command:

    ```bash
    ansible-playbook -i ansible/inventory.yml ansible/plays/setup_comfystream.yml
    ```

6. **Access the Server**:  
   Once the playbook finishes execution, you will receive the access URLs for the ComfyStream server.
