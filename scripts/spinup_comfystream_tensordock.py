"""Script used to spin up Comfystream on a suitable VM on TensorDock close to the user's
location.
"""

import os
import requests
import click
from typing import Dict, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from geopy.distance import geodesic
import sys
import time
from colorama import Fore, Style, init
import logging

TENSORDOCK_ENDPOINTS = {
    "auth_test": "https://marketplace.tensordock.com/api/v0/auth/test",
    "hostnodes": "https://marketplace.tensordock.com/api/v0/client/deploy/hostnodes",
    "deploy": "https://marketplace.tensordock.com/api/v0/client/deploy/single",
    "delete": "https://marketplace.tensordock.com/api/v0/client/delete/single",
}


# Requirements for host nodes.
MAX_PRICE = 0.5  # USD per hour
MIN_REQUIREMENTS = {
    "minvCPUs": 4,
    "minRAM": 16,  # GB
    "minStorage": 80,  # GB
    "minVRAM": 16,  # GB
    "minGPUCount": 1,
    "requiresRTX": True,
    "requiresGTX": False,
    "maxGPUCount": 1,
}
VM_SPECS = {
    "gpu_count": MIN_REQUIREMENTS["minGPUCount"],
    "vcpus": MIN_REQUIREMENTS["minvCPUs"],
    "ram": MIN_REQUIREMENTS["minRAM"],
    "storage": MIN_REQUIREMENTS["minStorage"],
    "internal_ports": str(set([22, 3000, 8889])),
    "operating_system": "Ubuntu 22.04 LTS",
}
CLOUD_INIT_PATH = os.path.join(
    os.path.dirname(__file__), "config", "cloud_init_comfystream.yaml"
)


class ColorFormatter(logging.Formatter):
    """Custom log formatter to add color to log messages based on log level."""

    # Define colors for each log level
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.RESET,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
        "SUCCESS": Fore.GREEN,  # Custom log level (not built-in)
    }

    def __init__(self, fmt="%(levelname)s - %(message)s"):
        """Initialize formatter with optional format."""
        super().__init__(fmt)
        init(autoreset=True)  # Initialize colorama for cross-platform support

    def format(self, record):
        """Apply color to log messages dynamically based on log level."""
        log_color = self.COLORS.get(record.levelname, Fore.RESET)
        record.msg = f"{log_color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


# Configure logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logger.handlers = []
logger.addHandler(handler)


geolocator = Nominatim(user_agent="tensordock_locator", timeout=5)


def load_cloud_init(cloud_init_path: str) -> str:
    """Load the cloud-init script from a file and convert it to a single string.
    Args:
        cloud_init_path: The path to the cloud-init script file.

    Returns:
        The cloud-init script as a single string.
    """
    with open(cloud_init_path, "r") as file:
        cloudinit_script = file.read()
    cloudinit_script = cloudinit_script.replace("\n", "\\n")
    return cloudinit_script


def filter_nodes_by_price(host_nodes: Dict, max_price: float) -> Dict:
    """Filter host nodes based on the maximum price.

    Args:
        host_nodes: Dictionary of host nodes.
        max_price: Maximum price per hour.

    Returns:
        Dictionary of filtered host nodes.
    """
    filtered_nodes = {}
    for node_id, node in host_nodes.items():
        total_price = (
            node["specs"]["cpu"]["price"]
            + sum(gpu["price"] for gpu in node["specs"]["gpu"].values())
            + node["specs"]["ram"]["price"]
            + node["specs"]["storage"]["price"]
        )
        if total_price <= max_price:
            filtered_nodes[node_id] = node
    return filtered_nodes


def filter_nodes_by_gpu_availability(host_nodes: Dict) -> Dict:
    """Filter host nodes based on the availability of GPUs and the minimum VRAM
    requirements. Remove GPUs that do not meet the requirements from the specs.

    Args:
        host_nodes: Dictionary of host nodes.

    Returns:
        Dictionary of filtered host nodes.
    """
    filtered_nodes = {}
    for node_id, node in host_nodes.items():
        gpu_models = node["specs"]["gpu"]
        compatible_gpus = {
            gpu_id: gpu
            for gpu_id, gpu in gpu_models.items()
            if gpu["amount"] > 0 and gpu["vram"] >= MIN_REQUIREMENTS["minVRAM"]
        }
        if compatible_gpus:
            node["specs"]["gpu"] = compatible_gpus
            filtered_nodes[node_id] = node
    return filtered_nodes


def filter_nodes_by_min_system_requirements(
    host_nodes: Dict, min_requirements: Dict
) -> Dict:
    """Filter host nodes based on the minimum system requirements.

    Args:
        host_nodes: Dictionary of host nodes.
        min_requirements: Dictionary of minimum requirements.

    Returns:
        Dictionary of filtered host nodes.
    """
    filtered_nodes = {}
    for node_id, node in host_nodes.items():
        restrictions = node["specs"]["restrictions"]
        for restriction in restrictions.values():
            if (
                min_requirements["minvCPUs"] >= restriction.get("cpu", {}).get("min", 0)
                and min_requirements["minRAM"]
                >= restriction.get("ram", {}).get("min", 0)
                and min_requirements["minStorage"]
                >= restriction.get("storage", {}).get("min", 0)
            ):
                filtered_nodes[node_id] = node
    return filtered_nodes


def get_current_location() -> Tuple:
    """Fetch the current location (latitude and longitude) using an IP geolocation API.

    Returns:
        Latitude and Longitude as a tuple (lat, lon).
    """
    try:
        response = requests.get("http://ip-api.com/json/")
        response.raise_for_status()
        data = response.json()
        return data["lat"], data["lon"]
    except requests.RequestException as e:
        logger.error(f"Error fetching current location: {e}")
        return None, None


def geocode_location(
    city: str, country: str, region: str, retries: int = 3, backoff_factor: float = 1
):
    """Geocode a location using Nominatim with retries and caching.

    Args:
        city: City name.
        country: Country name.
        region: Region name.
        retries: Number of retries for geocoding.
        backoff_factor: Backoff factor for retries.

    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found.
    """
    for attempt in range(retries):
        try:
            location = geolocator.geocode(f"{city}, {region}, {country}")
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            logger.warning(
                f"Geocoder timed out. Retrying in {backoff_factor * (2 ** attempt)} "
                f"seconds..."
            )
            time.sleep(backoff_factor * (2**attempt))
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            break  # Don't retry if it's a non-timeout error
    return None, None


def sort_nodes_by_distance(host_nodes: Dict) -> Dict:
    """Sort host nodes by distance from the current location.

    Args:
        host_nodes: Dictionary of host nodes.

    Returns:
        List of host nodes sorted by distance.
    """
    current_location = get_current_location()
    if not current_location:
        logger.error("Could not determine current location.")
        return []

    nodes_with_distance = []
    for node_id, node in host_nodes.items():
        node_location = geocode_location(
            node["location"]["city"],
            node["location"]["country"],
            node["location"]["region"],
        )
        if node_location:
            distance = geodesic(current_location, node_location).kilometers
            node["id"] = node_id
            nodes_with_distance.append((distance, node))

    # Sort nodes by distance
    nodes_with_distance.sort(key=lambda x: x[0])
    return [node for _, node in nodes_with_distance]


def read_ssh_key(public_ssh_key) -> str:
    """Retrieve the public SSH key from a file or directly.

    Args:
        public_ssh_key: The public SSH key or file path.

    Returns:
        The public SSH key as a string.
    """
    if public_ssh_key:
        if os.path.isfile(public_ssh_key):  # Check if it's a file path
            try:
                with open(public_ssh_key, "r") as key_file:
                    return key_file.read().strip()
            except Exception as e:
                logger.error(f"Failed to read SSH key file: {e}")
                sys.exit(1)
        else:
            return public_ssh_key.strip()  # Use the provided key directly
    return None


def is_strong_password(password: str, min_length: int = 35) -> bool:
    """Check if a password is strong enough.

    Args:
        password: The password to check.
        min_length: The minimum length of the password.

    Returns:
        True if the password is strong enough, otherwise False.
    """
    return (
        any(char.isupper() for char in password)
        and any(char.islower() for char in password)
        and any(char.isdigit() for char in password)
        and len(password) >= min_length
    )


class TensorDockController:
    """Controller class for interacting with the TensorDock API."""

    def __init__(self, api_key: str, api_token: str):
        """Initialize the TensorDockController with the API key and token.

        Args:
            api_key: The TensorDock API key.
            api_token: The TensorDock API token.
        """
        self.api_key = api_key
        self.api_token = api_token
        self._ensure_auth()

    def _ensure_auth(self):
        """Test the authentication with the TensorDock API.

        Raises:
            requests.HTTPError: If the authentication fails.
        """
        response = requests.post(
            TENSORDOCK_ENDPOINTS["auth_test"],
            data={"api_key": self.api_key, "api_token": self.api_token},
        )
        response.raise_for_status()
        if not response.json()["success"]:
            raise requests.HTTPError("Authentication failed.")

    def _fetch_host_nodes(self, min_host_requirements: Dict) -> Dict:
        """Fetch host nodes from TensorDock API with specified minimum settings.

        Args:
            min_host_requirements: Dictionary of minimum requirements.

        Returns:
            dict: Dictionary of compatible host nodes.
        """
        try:
            response = requests.get(
                TENSORDOCK_ENDPOINTS["hostnodes"],
                params=min_host_requirements,
                headers={"Authorization": f"Bearer {self.api_key}:{self.api_token}"},
            )
            response.raise_for_status()
            if response.json()["success"]:
                return response.json()["hostnodes"]
        except requests.RequestException as e:
            logger.error(f"Error fetching compatible host nodes: {e}")
        return {}

    def fetch_compatible_host_nodes(
        self, min_host_requirements: Dict, max_price: float
    ) -> Dict:
        """Fetch compatible host nodes based on the minimum requirements and maximum
        price.

        Args:
            min_host_requirements: Dictionary of minimum requirements.
            max_price: Maximum price per hour.

        Returns:
            Dictionary of compatible host nodes.
        """
        host_nodes = self._fetch_host_nodes(min_host_requirements)
        logger.debug(f"Found {len(host_nodes)} host nodes.")
        host_nodes = filter_nodes_by_price(host_nodes, max_price)
        logger.debug(f"Found {len(host_nodes)} host nodes within price range.")
        host_nodes = filter_nodes_by_gpu_availability(host_nodes)
        logger.debug(f"Found {len(host_nodes)} host nodes with available GPUs.")
        host_nodes = filter_nodes_by_min_system_requirements(
            host_nodes, min_host_requirements
        )
        logger.debug(
            f"Found {len(host_nodes)} host nodes meeting minimum requirements."
        )
        return host_nodes

    def deploy_vm(
        self,
        name: str,
        hostnode_id: str,
        gpu_model: str,
        external_ports: list[int],
        password: str = None,
        public_ssh_key: str = None,
        cloud_init_path: str = CLOUD_INIT_PATH,
    ) -> Dict:
        """Deploy a VM on a host node with the specified location, OS, and password.

        Args:
            name: The name of the VM.
            hostnode_id: The ID of the host node.
            gpu_model: The GPU model of the VM.
            external_ports: List of external ports to open.
            password: The password for the VM (if provided).
            public_ssh_key: The public SSH key for the VM (if provided).
            cloud_init_path: The path to the cloud-init configuration file.

        Returns:
            The response from the TensorDock API if successful, otherwise an empty
            dictionary.
        """

        vm_specs = {
            "api_key": self.api_key,
            "api_token": self.api_token,
            "name": name,
            "hostnode": hostnode_id,
            "gpu_model": gpu_model,
            "external_ports": str(external_ports),
            **VM_SPECS,
        }
        if public_ssh_key:
            vm_specs["public_ssh_key"] = public_ssh_key
        if password:
            vm_specs["password"] = password
        if cloud_init_path:
            vm_specs["cloudinit_script"] = load_cloud_init(cloud_init_path)

        try:
            response = requests.post(TENSORDOCK_ENDPOINTS["deploy"], data=vm_specs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            error_message = response.json().get("error", None)
            error_str = (
                f"Error deploying VM: {error_message}" if error_message else str(e)
            )
            logger.error(error_str)
        return {}

    def delete_vm(self, vm_id: str) -> bool:
        """Delete a VM with the specified ID.

        Args:
            vm_id: The ID of the VM to delete.

        Returns:
            True if the VM was deleted successfully, otherwise False.
        """
        try:
            response = requests.post(
                TENSORDOCK_ENDPOINTS["delete"],
                data={
                    "api_key": self.api_key,
                    "api_token": self.api_token,
                    "server": vm_id,
                },
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except requests.RequestException as e:
            logger.error(f"Error deleting VM: {e}")
        return False


@click.command()
@click.option(
    "--api-key",
    default=lambda: os.environ.get("TENSORDOCK_API_KEY", ""),
    prompt="TensorDock API Key",
    help="Your TensorDock API key.",
    hide_input=True,
    prompt_required=False,
)
@click.option(
    "--api-token",
    default=lambda: os.environ.get("TENSORDOCK_API_TOKEN", ""),
    prompt="TensorDock API Token",
    help="Your TensorDock API token.",
    hide_input=True,
    prompt_required=False,
)
@click.option(
    "--delete",
    default=None,
    help="Delete the VM with the specified ID.",
)
@click.option(
    "--max-price",
    default=MAX_PRICE,
    help="Maximum price per hour.",
)
@click.option(
    "--vm-name",
    default=f"comfystream-{int(time.time())}",
    help="Name of the VM.",
)
@click.option(
    "--password",
    default=None,
    help="Password for the VM.",
)
@click.option(
    "--public-ssh-key",
    default=None,
    help="Public SSH key for the VM.",
)
def main(
    api_key,
    api_token,
    vm_name,
    max_price,
    password,
    public_ssh_key,
    delete,
):
    """Main function that collects command line arguments and deploys Comfystream on a
    suitable VM on TensorDock close to the user's location.

    Args:
        api_key: The TensorDock API key.
        api_token: The TensorDock API token.
        vm_name: The name of the VM.
        max_price: The maximum price per hour.
        password: The password for the VM.
        public_ssh_key: The public SSH key for the VM.
        delete: The ID of the VM to delete.
    """
    api_key = api_key or click.prompt("TensorDock API Key", hide_input=True)
    api_token = api_token or click.prompt("TensorDock API Token", hide_input=True)

    controller = TensorDockController(api_key, api_token)
    if delete:
        logger.info(f"Deleting VM '{delete}'...")
        if controller.delete_vm(delete):
            logger.info(
                f"{ColorFormatter.COLORS['SUCCESS']}Successfully deleted VM '{delete}'.{Style.RESET_ALL}"
            )
        else:
            logger.error(f"Failed to delete VM '{delete}'.")
        sys.exit(0)

    public_ssh_key = read_ssh_key(public_ssh_key)
    if not password and not public_ssh_key:
        logger.error("You must provide either a password or a public SSH key.")
        sys.exit(1)
    if password and public_ssh_key:
        logger.error("You cannot provide both a password and a public SSH key.")
        sys.exit(1)
    if password and not is_strong_password(password):
        logger.error("The password is not strong enough.")
        sys.exit(1)

    # Fetch and filter host nodes.
    logger.info(f"Looking for a suitable host within ${max_price} per hour...")
    logger.info("Fetching host nodes and filtering by requirements...")
    filtered_nodes = controller.fetch_compatible_host_nodes(MIN_REQUIREMENTS, max_price)
    if not filtered_nodes:
        logger.error("No suitable host nodes found.")
        sys.exit(1)
    logger.info(f"Found {len(filtered_nodes)} suitable host nodes.")

    logger.info("Sort nodes by distance from current location...")
    sorted_host_nodes = sort_nodes_by_distance(filtered_nodes)
    if not sorted_host_nodes:
        logger.error("Something went wrong while sorting host nodes by distance.")
        sys.exit(1)

    # Try to deploy VM on the closest nodes until successful.
    logger.info(
        f"Attempting VM deployment on {len(sorted_host_nodes)} closest nodes..."
    )
    for ii, node in enumerate(sorted_host_nodes):
        compatible_gpus = [
            gpu
            for gpu, details in node["specs"]["gpu"].items()
            if details["vram"] >= MIN_REQUIREMENTS["minVRAM"]
        ]
        if not compatible_gpus:
            logger.warning(
                f"No compatible GPU found on {node['id']} "
                f"({node['location']['city']}). Skipping."
            )
            continue
        for jj, gpu in enumerate(compatible_gpus):
            logger.info(
                f"Attempting deployment on node '{node['id']}' located in "
                f"{node['location']['city']}, {node['location']['country']} using "
                f"GPU '{gpu}'..."
            )
            available_ports = node["networking"]["ports"][:3]
            formatted_ports = str(set(available_ports))
            node_info = controller.deploy_vm(
                name=vm_name,
                hostnode_id=node["id"],
                gpu_model=gpu,
                external_ports=formatted_ports,
                password=password,
                public_ssh_key=public_ssh_key,
            )
            if node_info:
                logger.info(
                    f"{ColorFormatter.COLORS['SUCCESS']}successfully deployed on "
                    f"'{node['id']}' ({node['location']['city']}).{Style.RESET_ALL}"
                )
                break
            else:
                warning_msg = (
                    f"Deployment failed on {node['location']['city']} using GPU "
                    f"'{gpu}'."
                )
                if jj < len(compatible_gpus) - 1:
                    warning_msg += " Trying next GPU..."
                logger.warning(warning_msg)
        else:
            warning_msg = (
                f"Deployment failed on {node['location']['city']} for all GPUs. "
            )
            if ii < len(sorted_host_nodes) - 1:
                warning_msg += "Trying next node..."
            logger.warning(warning_msg)
            continue
        break
    else:
        logger.error("All deployment attempts failed. No VM was deployed.")
        sys.exit(1)

    logger.warning(
        "Remember to remove the VM after use to avoid unnecessary costs. Run "
        f"'spinup_comfystream_tensordock.py --delete {node['id']}' to remove the VM."
    )

    # Print VM URLs and QR codes for easy access.
    logger.info(
        "Comfystream container will be downloaded and started on the VM. This might "
        "take a few minutes..."
    )
    logger.info(
        "Once the container is running, you can access the Comfystream UI and server "
        "at the following URLs:"
    )
    comfystream_ui_url = f"http://{node_info['ip']}:{available_ports[1]}"
    comfystream_server_url = f"http://{node_info['ip']}:{available_ports[2]}"
    ssh_command = f"ssh root@{node_info['ip']} -p {available_ports[0]}"
    logger.info(f"{Fore.GREEN}Comfystream UI:{Style.RESET_ALL} {comfystream_ui_url}")
    logger.info(
        f"{Fore.GREEN}Comfystream Server:{Style.RESET_ALL} {comfystream_server_url}"
    )
    logger.info(f"{Fore.GREEN}SSH into the VM:{Style.RESET_ALL} {ssh_command}")

    # Ping the server to check if it's up.
    logger.info("Waiting for the Comfystream container to start...")
    retry_interval = 30  # s
    time.sleep(retry_interval)
    started = False
    while not started:
        try:
            response = requests.get(comfystream_server_url)
            response.raise_for_status()
            if response.status_code == 200:
                logger.info(
                    f"{Fore.GREEN}Comfystream container is up and running! 🚀{Style.RESET_ALL}"
                )
                started = True
                break
        except requests.RequestException as e:
            logger.warning(
                f"Comfystream server not yet up. Retrying ping in {retry_interval} seconds..."
            )
            time.sleep(retry_interval)

    try:
        import qrcode
        import qrcode_terminal

        logger.info("Generating QR codes for easy access:")
        logger.info("Comfystream UI QR Code:")
        qrcode_terminal.draw(comfystream_ui_url)

        logger.info("Comfystream Server QR Code:")
        qrcode_terminal.draw(comfystream_server_url)

        logger.info("SSH into the VM QR Code:")
        qrcode_terminal.draw(ssh_command)
    except ImportError:
        logger.warning(
            "qrcode and qrcode_terminal modules are not installed. Skipping QR code generation."
        )


if __name__ == "__main__":
    logger.info("Starting Comfystream TensorDock deployment...")
    main()
