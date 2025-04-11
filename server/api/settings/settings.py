import os
from pathlib import Path
import psutil
import subprocess
import sys

async def set_twilio_account_info(account_sid, auth_token):
    if not account_sid is None:
        os.environ["TWILIO_ACCOUNT_SID"] = account_sid
    if not auth_token is None:
        os.environ["TWILIO_AUTH_TOKEN"] = auth_token

async def restart_comfyui(workspace_dir):
    subprocess.run(["supervisorctl", "restart", "comfyui"], check=False)
