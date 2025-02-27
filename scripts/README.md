# ComfyUI Helper Scripts

This directory contains various helper scripts designed to streamline working with ComfyStream:

- `spinup_comfystream_tensordock.py`: Spins up a ComfyStream instance on a [Tensordock server](https://tensordock.com/), installs dependencies, and starts the server.

## Usage Instructions

### Spinup TensorDock ComfyStream Instance

1. **Create a Tensordock Account**: Register at [Tensordock](https://dashboard.tensordock.com/register), attach a credit card, and create an API key and token.
2. **Check Available Options** *(Optional but Recommended)*:  
   To see all available script options, run:

    ```bash
    python spinup_comfystream_tensordock.py --help
    ```

3. **Run the Script**:  
   Execute the following command to spin up a ComfyStream instance:

    ```bash
    python spinup_comfystream_tensordock.py --api-key <API_KEY> --api-token <API_TOKEN>
    ```

4. **Access the Server**:  
   The script will set up the instance, install dependencies, and start the server. This process will take a few minutes. Once completed, you can access the ComfyStream server and UI using the provided URLs.

5. **Stop the Server**:  
   To stop the server, run:

    ```bash
    python spinup_comfystream_tensordock.py --delete <VM_ID>
    ```

   Replace `<VM_ID>` with the ID of the VM you want to delete. You can find the VM ID in the script logs or the [Tensordock dashboard](https://dashboard.tensordock.com/).

> [!NOTE]  
> By default, the ComfyUI port is not publicly exposed for security reasons. However, you can enable public access using the `--expose-comfyui` flag. Credentials will be provided in the logs, but keep in mind that this is not a foolproof security measure, and exposing the port may pose security risks.

> [!IMPORTANT]  
> Due to a known bug in TensorDock, the server may sometimes fail to detect the NVIDIA GPU until it is rebooted. If you experience GPU-related issues, try restarting the server first.
