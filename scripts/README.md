# ComfyUI Helper Scripts

This directory contains various helper scripts designed to streamline working with ComfyStream:

- `spinup_comfystream_tensordock.py`: Spins up a ComfyStream instance on a [Tensordock server](https://tensordock.com/), installs dependencies, and starts the server.

## Usage Instructions

### Spinup TensorDock ComfyStream Instance

1. **Create a Tensordock Account**: Register at [Tensordock](https://dashboard.tensordock.com/register), attach a credit card, and create an API key and token.
2. **Set Up a Python Virtual Environment**:
   Create and activate a virtual environment using [Conda](https://docs.anaconda.com/miniconda/) and install the required dependencies:

    ```bash
    conda create -n comfystream python=3.8
    conda activate comfystream
    pip install -r requirements.txt
    ```

3. **Check Available Options** *(Optional but Recommended)*:  
   To see all available script options, run:

    ```bash
    python spinup_comfystream_tensordock.py --help
    ```

4. **Run the Script**:  
   Execute the following command to spin up a ComfyStream instance:

    ```bash
    python spinup_comfystream_tensordock.py --api-key <API_KEY> --api-token <API_TOKEN>
    ```

5. **Access the Server**:  
   The script will set up the instance, install dependencies, and start the server. This process will take a few minutes. Once completed, you can access the ComfyStream server and UI using the provided URLs.

6. **Stop the Server**:  
   To stop the server, run:

    ```bash
    python spinup_comfystream_tensordock.py --delete <VM_ID>
    ```

   Replace `<VM_ID>` with the ID of the VM you want to delete. You can find the VM ID in the script logs or the [Tensordock dashboard](https://dashboard.tensordock.com/).

> [!WARNING]
> If you see `max retries exceeded with url` errors, the VM was likely created but is inaccessible. Check the [TensorDock dashboard](https://dashboard.tensordock.com/instances), delete the VM, wait 2-3 minutes, then run the script again.
