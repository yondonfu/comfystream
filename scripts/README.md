# ComfyUI Helper Scripts

This directory contains various helper scripts designed to streamline working with ComfyStream:

- `spinup_comfystream_tensordock.py`: Spins up a ComfyStream instance on a [Tensordock server](https://tensordock.com/), installs dependencies, and starts the server.

## Usage Instructions

### Spinup TensorDock ComfyStream Instance

1. **Create a Tensordock Account**: Register at [Tensordock](https://dashboard.tensordock.com/register), attach a credit card, and create an API key and token.
2. **Run the Script**: Execute the following command to spin up a ComfyStream instance:

    ```bash
    python spinup_comfystream_tensordock.py --api-key <API_KEY> --api-token <API_TOKEN>
    ```

3. **Access the Server**: The script will set up the instance, install dependencies, and start the server. This process will take a few minutes. After completed you can access the ComfyStream server and UI using the provided URLs. 

4. **Stop the Server**: To stop the server, run:

    ```bash
    python spinup_comfystream_tensordock.py --delete <VM_ID>
    ```

    Replace `<VM_ID>` with the ID of the VM you want to delete. You can find the VM ID in the script logs or the Tensordock dashboard.

> [!NOTE]  
> The ComfyUI port is not publicly exposed due to the lack of security measures, such as an [Nginx server](https://nginx.org/en/). However, if needed, you can enable it in the [Tensordock dashboard](https://dashboard.tensordock.com/).
