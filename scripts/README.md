# ComfyUI Helper Scripts

This directory contains helper scripts to simplify the deployment and management of **ComfyStream**:

- **Ansible Playbook (`ansible/plays/setup_comfystream.yml`)** – Deploys ComfyStream on any cloud provider.  
- **`spinup_comfystream_tensordock.py`** – Fully automates VM creation and ComfyStream setup on a [TensorDock server](https://tensordock.com/).  

## Usage Instructions

### Ansible Playbook (Cloud-Agnostic Deployment)

This repository includes an [Ansible playbook](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html) to deploy ComfyStream on any cloud provider. Follow the steps below:

1. **Create a VM**:  
   Deploy a VM on a cloud provider such as [TensorDock](https://marketplace.tensordock.com/deploy?gpu=geforcertx4090-pcie-24gb&gpuCount=1&ramAmount=16&vcpuCount=4&storage=100&os=Ubuntu-22.04-LTS), AWS, Google Cloud, or Azure with the following minimum specifications:
   - **GPU**: 20GB VRAM  
   - **RAM**: 16GB  
   - **CPU**: 4 vCPUs  
   - **Storage**: 100GB

   > [!TIP]
   > You can use the `spinup_comfystream_tensordock.py --bare-vm` script to create a compatible VM on TensorDock.

2. **Open Required Ports**:  
   Ensure the following ports are open **inbound and outbound** on the VM's firewall/security group:
   - **SSH (Port 22)** – Remote access  
   - **HTTPS (Port 8189)** – ComfyStream access  
  
3. **Install Ansible**:  
   Follow the [official Ansible installation guide](https://docs.ansible.com/ansible/latest/installation_guide/index.html).

4. **Configure the Inventory File**:
   Add the VM’s public IP to `ansible/inventory.yml`.

5. **Run the Playbook**:  
   Execute:

    ```bash
    ansible-playbook -i ansible/inventory.yaml ansible/plays/setup_comfystream.yaml
    ```

6. **Access the Server**:  
   After successful execution, the access URLs for **ComfyStream** will be displayed.

> [!TIP]
> The [ComfyStream Docker image](https://hub.docker.com/r/livepeer/comfystream/tags) is **~20GB**. To check download progress, SSH into the VM and run:
>
> ```bash
> docker pull livepeer/comfystream:latest
> ```

### TensorDock Spinup Script (Fully Automated)

The `spinup_comfystream_tensordock.py` script automates VM provisioning, setup, and server launch on [TensorDock](https://tensordock.com/). Follow the steps below:

1. **Create a TensorDock Account**: Sign up at [Tensordock](https://dashboard.tensordock.com/register), add a payment method, and generate API credentials.

2. **Set Up a Python Virtual Environment**:
   To prevent dependency conflicts, create and activate a virtual environment with [Conda](https://docs.anaconda.com/miniconda/) and install the required dependencies:

    ```bash
   conda create -n comfystream python=3.8
   conda activate comfystream
   pip install -r requirements.txt
   ```

3. **View Available Script Options** *(Optional)*:  
   To see all available options, run:

    ```bash
    python spinup_comfystream_tensordock.py --help
    ```

4. **Run the Script**:  
   Execute the following command to provision a VM and set up ComfyStream automatically:

    ```bash
    python spinup_comfystream_tensordock.py --api-key <API_KEY> --api-token <API_TOKEN>
    ```

5. **Access the Server**:  
   Once the setup is complete, the script will display the URLs to access ComfyStream.

6. **Stop & Delete the VM** *(When No Longer Needed)*:
   To stop and remove the instance, run:

    ```bash
    python spinup_comfystream_tensordock.py --delete <VM_ID>
    ```

   Replace `<VM_ID>` with the VM ID found in the script logs or the [TensorDock dashboard](https://dashboard.tensordock.com/instances).

> [!WARNING]
> If you encounter `max retries exceeded with URL` errors, the VM might have been created but is inaccessible.  
> Check the [TensorDock dashboard](https://dashboard.tensordock.com/instances), delete the VM manually, wait **2-3 minutes**, then rerun the script.
