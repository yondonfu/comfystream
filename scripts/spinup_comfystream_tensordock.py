"""Script used to spin up Comfystream and ComfyUI on a suitable VM on TensorDock close
to the user's location.
"""

import base64
import logging
import os
import secrets
import string
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bcrypt
import click
import requests
from colorama import Fore, Style, init
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

TENSORDOCK_ENDPOINTS = {
    "auth_test": "https://marketplace.tensordock.com/api/v0/auth/test",
    "hostnodes": "https://marketplace.tensordock.com/api/v0/client/deploy/hostnodes",
    "deploy": "https://marketplace.tensordock.com/api/v0/client/deploy/single",
    "delete": "https://marketplace.tensordock.com/api/v0/client/delete/single",
}


# Requirements for host nodes.
DEFAULT_MAX_PRICE = 0.5  # USD per hour
MIN_REQUIREMENTS = {
    "minvCPUs": 4,
    "minRAM": 16,  # GB
    "minStorage": 100,  # GB
    "minVRAM": 20,  # GB
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
    "internal_ports": [22, 8189],
    "operating_system": "Ubuntu 22.04 LTS",
}
CADDY_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "comfyui.caddy.j2"
)
CLOUD_INIT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "cloud_init_comfystream.yaml.j2"
)
PASSWORD_PLACEHOLDER = "{{ password_hash }}"
COMFYSTREAM_CADDY_PLACEHOLDER = "{{ comfystream_caddy_placeholder }}"
DOCKER_IMAGE_PLACEHOLDER = "{{ docker_image_placeholder }}"


class ColorFormatter(logging.Formatter):
    """Custom log formatter to add color to log messages based on log level."""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.RESET,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
        "SUCCESS": Fore.GREEN,  # Custom log level (not built-in).
    }

    def __init__(self, fmt="%(levelname)s - %(message)s"):
        """Initialize formatter with optional format.

        Args:
            fmt (str): The format string for the log messages.
        """
        super().__init__(fmt)
        init(autoreset=True)  # Initialize colorama for cross-platform support.

    def format(self, record):
        """Apply color to log messages dynamically based on log level.

        Args:
            record: The log record to format.

        Returns:
            str: The formatted log message with color.
        """
        log_color = self.COLORS.get(record.levelname, Fore.RESET)
        record.msg = f"{log_color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logger.handlers = []
logger.addHandler(handler)


geolocator = Nominatim(user_agent="tensordock_locator", timeout=5)
console = Console()


def display_login_info(
    comfyui_url: str = None,
    comfyui_username: str = None,
    comfyui_password: str = None,
    ssh_command: str = None,
):
    """Display VM login information, but only for values that are provided.

    Args:
        comfyui_url: The ComfyUI URL.
        comfyui_username: The ComfyUI username.
        comfyui_password: The ComfyUI password.
        ssh_command: The SSH command.
    """
    labels_and_styles = {
        "ComfyUI url: ": (comfyui_url, "yellow"),
        "ComfyUI username: ": (comfyui_username, "cyan"),
        "ComfyUI password: ": (comfyui_password, "cyan"),
        "SSH Command: ": (ssh_command, "green"),
    }

    content_elements = []
    for label, (value, style) in labels_and_styles.items():
        if value:
            text = Text(label, style=style)
            text.append(value, style="white")
            content_elements.append(text)

    if not content_elements:
        logger.warning("No access information available to display.")
        return

    final_content = Text.assemble(
        *(sum(zip(content_elements, ["\n"] * len(content_elements)), ())[:-1])
    )
    console.print(
        Panel(
            final_content,
            title="[blue]Access Information[/blue]",
            border_style="blue",
            expand=False,
        )
    )


def generate_strong_password(length: int = 60) -> str:
    """Generate a strong password with a mix of letters, digits, and special characters.

    Args:
        length: The length of the password.

    Returns:
        A strong password.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(characters) for _ in range(length))
    return password


def is_strong_password(password: str, min_length: int = 32) -> bool:
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


def hash_password(password: str) -> str:
    """Create hash a password using bcrypt.

    Args:
        password: The password to hash.

    Returns:
        The hashed password.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode().strip()


def get_cloud_init_script(
    comfyui_password: str, docker_image: str = "livepeer/comfystream:latest"
) -> str:
    """Generate the cloud-init script using the template and replace placeholders.

    Args:
        comfyui_password: The password used to protect the ComfUI interface.
        docker_image: The Docker image to use for the Comfystream deployment (e.g.
            'repository/image:tag').

    Returns:
        The cloud-init script as a string.
    """
    # Open cloud init template and read its content.
    try:
        with open(CLOUD_INIT_TEMPLATE_PATH, "r", encoding="utf-8") as file:
            cloud_init_content = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Cloud-init template not found: {CLOUD_INIT_TEMPLATE_PATH}"
        )
    cloud_init_content = cloud_init_content.replace("\r\n", "\n").replace(
        "\r", "\n"
    )  # Normalize line endings

    # Open Caddyfile template and read its content.
    try:
        with open(CADDY_TEMPLATE_PATH, "r", encoding="utf-8") as file:
            caddyfile_content = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Caddyfile template not found: {CADDY_TEMPLATE_PATH}")

    # Inject ComfyUI password and convert to base64.
    encoded_password = hash_password(comfyui_password)
    caddyfile_content = caddyfile_content.replace(
        PASSWORD_PLACEHOLDER, encoded_password
    )
    caddy_config_b64 = base64.b64encode(caddyfile_content.encode()).decode()

    # Replace placeholders in the cloud-init script and return the final content.
    replacements = {
        COMFYSTREAM_CADDY_PLACEHOLDER: caddy_config_b64,
        DOCKER_IMAGE_PLACEHOLDER: docker_image,
    }
    for placeholder, value in replacements.items():
        cloud_init_content = cloud_init_content.replace(placeholder, value)
    return cloud_init_content


def format_ports_as_set(ports: List) -> str:
    """Format a list of ports as a string that looks like a set.

    Args:
        ports: List of ports.

    Returns:
        A string that looks like a set.
    """
    return "{" + ", ".join(map(str, ports)) + "}"


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
    location_str: str, retries: int = 3, backoff_factor: float = 1
) -> Tuple[Optional[float], Optional[float]]:
    """Geocode a location using Nominatim with retries and caching.

    Args:
        location_str: Location string to geocode (e.g. 'City, Country, Region)').
        retries: Number of retries for geocoding.
        backoff_factor: Backoff factor for retries.

    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found.
    """
    for attempt in range(retries):
        try:
            location = geolocator.geocode(location_str)
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
            break  # Don't retry if it's a non-timeout error.
    return None, None


def sort_nodes_by_distance(
    host_nodes: Dict, location: Optional[Tuple[float, float]]
) -> List:
    """Sort host nodes by distance from the current location.

    Args:
        host_nodes: Dictionary of host nodes.
        location: Location to sort the nodes relative to (latitude, longitude).

    Returns:
        List of host nodes sorted by distance.
    """
    if not location:
        location = get_current_location()
        if not location:
            logger.error("Could not determine current location.")
            return []

    nodes_with_distance = []
    for node_id, node in host_nodes.items():
        location_parts = [
            node["location"].get("city"),
            node["location"].get("region"),
            node["location"].get("country"),
        ]
        location_str = ", ".join(filter(None, location_parts))
        node_location = geocode_location(location_str=location_str)
        if node_location:
            distance = geodesic(location, node_location).kilometers
            node["id"] = node_id
            nodes_with_distance.append((distance, node))

    nodes_with_distance.sort(key=lambda x: x[0])
    return [node for _, node in nodes_with_distance]


def read_ssh_key(public_ssh_key: str) -> str:
    """Retrieve the public SSH key from a file or directly.

    Args:
        public_ssh_key: The public SSH key or file path.

    Returns:
        The public SSH key as a string.
    """
    if public_ssh_key:
        key_path = Path(public_ssh_key)
        if key_path.is_file():
            try:
                with open(public_ssh_key, "r") as key_file:
                    return key_file.read().strip()
            except Exception as e:
                logger.error(f"Failed to read SSH key file: {e}")
                sys.exit(1)
        else:
            return public_ssh_key.strip()  # Use the provided key directly.
    return None


def get_vm_access_info(node_info: Dict) -> Tuple[str, str]:
    """Get SSH access command and ComfyUI URL for a deployed VM.

    Args:
        node_info: Dictionary of node information.

    Returns:
        Tuple of SSH command and ComfyUI URL.
    """
    available_ports = list(node_info["port_forwards"].keys())
    ssh_command = f"ssh -p {available_ports[0]} user@{node_info['ip']}"
    comfyui_url = f"https://{node_info['ip']}:{available_ports[1]}"
    return ssh_command, comfyui_url


def generate_qr_code(url: str):
    """Generates QR codes for a given URL.

    Args:
        comfystream_ui_url: URL to the Comfystream UI.
        comfystream_server_url: URL to the Comfystream Server.
    """
    try:
        import qrcode_terminal

        qrcode_terminal.draw(url)
    except ImportError:
        logger.warning(
            "qrcode_terminal module is not installed. Skipping QR code generation."
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
        logger.debug(f"Initial host nodes count: {len(host_nodes)}")
        host_nodes = filter_nodes_by_price(host_nodes, max_price)
        logger.debug(f"Host nodes within price range: {len(host_nodes)}")
        host_nodes = filter_nodes_by_gpu_availability(host_nodes)
        logger.debug(f"Host nodes with available GPUs: {len(host_nodes)}")
        host_nodes = filter_nodes_by_min_system_requirements(
            host_nodes, min_host_requirements
        )
        logger.debug(f"Host nodes meeting minimum requirements: {len(host_nodes)}")
        return host_nodes

    def deploy_vm(
        self,
        name: str,
        hostnode_id: str,
        gpu_model: str,
        internal_ports: List[int],
        external_ports: List[int],
        cloud_init_script: str = None,
        password: str = None,
        public_ssh_key: str = None,
    ) -> Dict:
        """Deploy a VM on a host node with the specified settings and cloud init script.

        Args:
            name: The name of the VM.
            hostnode_id: The ID of the host node.
            gpu_model: The GPU model of the VM.
            internal_ports: List of internal ports to open.
            external_ports: List of external ports to open.
            cloud_init_script: The cloud-init script for the VM (if provided).
            password: The password for the VM (if provided).
            public_ssh_key: The public SSH key for the VM (if provided).

        Returns:
            The response from the TensorDock API if successful, otherwise an empty
            dictionary.
        """
        vm_specs = {
            **VM_SPECS,
            "api_key": self.api_key,
            "api_token": self.api_token,
            "name": name,
            "hostnode": hostnode_id,
            "gpu_model": gpu_model,
            "internal_ports": format_ports_as_set(internal_ports),
            "external_ports": format_ports_as_set(external_ports),
        }
        if public_ssh_key:
            vm_specs["public_ssh_key"] = public_ssh_key
        if password:
            vm_specs["password"] = password
        if cloud_init_script:
            vm_specs["cloudinit_script"] = cloud_init_script

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

    def deploy_vm_on_tensordock(
        self,
        host_nodes: Dict,
        vm_name: str,
        password: str,
        public_ssh_key: str,
        comfyui_password: str,
        location: Tuple[int, int] = None,
        docker_image: str = "livepeer/comfystream:latest",
        bare_vm: bool = False,
    ):
        """Deploys a VM on TensorDock, optionally with Comfystream.

        Args:
            host_nodes: List of compatible host nodes.
            vm_name: Name of the VM.
            password: Password for the VM (if provided).
            public_ssh_key: Public SSH key for the VM (if provided).
            comfyui_password: Password for the ComfyUI interface (ignored if
                bare_vm=True).
            location: Location to search for host nodes close to.
            docker_image: Docker image to use for Comfystream (ignored if
                bare_vm=True).
            bare_vm: If True, deploy a clean VM without ComfyStream.

        Returns:
            Information about the deployed node, or None if deployment failed.
        """
        logger.info("Sorting nodes by distance from current location...")
        sorted_host_nodes = sort_nodes_by_distance(
            host_nodes=host_nodes, location=location
        )
        if not sorted_host_nodes:
            logger.error("Something went wrong while sorting host nodes by distance.")
            return None

        # Loop through sorted host nodes and try to deploy on the closest one.
        logger.info(
            f"Attempting VM deployment on {len(sorted_host_nodes)} closest node..."
        )
        cloud_init_script = None
        if not bare_vm:
            cloud_init_script = get_cloud_init_script(
                comfyui_password=comfyui_password,
                docker_image=docker_image,
            )
        for node_idx, node in enumerate(sorted_host_nodes):
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

            # Loop through compatible GPUs and try to deploy on the node.
            internal_ports = VM_SPECS["internal_ports"]
            available_ports = node["networking"]["ports"][: len(internal_ports)]
            for gpu_idx, gpu in enumerate(compatible_gpus):
                logger.info(
                    f"Attempting deployment on node '{node['id']}' in "
                    f"{node['location']['city']}, {node['location']['country']} using "
                    f"GPU '{gpu}'."
                )
                node_info = self.deploy_vm(
                    name=vm_name,
                    hostnode_id=node["id"],
                    gpu_model=gpu,
                    internal_ports=internal_ports,
                    external_ports=available_ports,
                    cloud_init_script=cloud_init_script,
                    password=password,
                    public_ssh_key=public_ssh_key,
                )

                if node_info:
                    logger.info(
                        f"{ColorFormatter.COLORS['SUCCESS']}VM successfully deployed "
                        f"on '{node['id']}' ({node['location']['city']})."
                        f"{Style.RESET_ALL}"
                    )
                    return node_info
                if gpu_idx < len(compatible_gpus) - 1:
                    logger.warning(
                        f"Deployment failed on {node['location']['city']} using GPU "
                        f"'{gpu}'. Trying next GPU..."
                    )
            if node_idx < len(sorted_host_nodes) - 1:
                logger.warning(
                    f"Deployment failed on {node['location']['city']} for all GPUs. "
                    "Trying next node..."
                )
        logger.error("All deployment attempts failed. No VM was deployed.")
        return None


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
    default=DEFAULT_MAX_PRICE,
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
@click.option(
    "--qr-code",
    is_flag=True,
    help="Generate ComfyUI QR code for easy access. Ignored for bare VMs.",
)
@click.option(
    "--location",
    default=None,
    help=(
        "Where to search for host nodes (e.g. City, Country, Region). If not provided, "
        "the current location is used."
    ),
)
@click.option(
    "--docker-image",
    default="livepeer/comfystream:latest",
    help=(
        "Docker image to use for the Comfystream deployment (e.g. "
        "'repository/image:tag')."
    ),
)
@click.option(
    "--bare-vm",
    is_flag=True,
    help="Spin up a VM without setting up ComfyStream (creates a clean VM).",
)
def main(
    api_key,
    api_token,
    delete,
    vm_name,
    max_price,
    password,
    public_ssh_key,
    qr_code,
    location,
    docker_image,
    bare_vm,
):
    """Main function that collects command line arguments and deploys or deletes a VM
    with Comfystream on TensorDock close to the user's location.

    Args:
        api_key: The TensorDock API key.
        api_token: The TensorDock API token.
        delete: The ID of the VM to delete.
        vm_name: The name of the VM.
        max_price: The maximum price per hour.
        password: The password for the VM.
        public_ssh_key: The public SSH key for the VM.
        qr_code: Whether to generate QR codes for easy access.
        location: The location to search for host nodes (e.g. City, Country, Region).
        docker_image: The Docker image to use for the Comfystream deployment.
        bare_vm: Whether to spin up a VM without setting up ComfyStream.
    """
    api_key = api_key or click.prompt("TensorDock API Key", hide_input=True)
    api_token = api_token or click.prompt("TensorDock API Token", hide_input=True)
    vm_type = "ComfyStream" if not bare_vm else "bare"
    logger.info(
        f"Starting {Fore.BLUE}{vm_type}{Style.RESET_ALL} TensorDock deployment..."
    )

    controller = TensorDockController(api_key, api_token)

    if location:
        location = geocode_location(location_str=location)

    if delete:
        logger.info(f"Deleting VM '{delete}'...")
        if controller.delete_vm(delete):
            logger.info(
                f"{ColorFormatter.COLORS['SUCCESS']}Successfully deleted VM '{delete}'."
                f"{Style.RESET_ALL}"
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
    if password and not is_strong_password(password, min_length=32):
        logger.error(
            "Password strength insufficient: must be at least 32 characters long and "
            "include uppercase, lowercase, digits, and special characters."
        )
        sys.exit(1)

    logger.info(f"Looking for a suitable host within ${max_price} per hour...")
    logger.info("Fetching host nodes and filtering by requirements...")
    filtered_nodes = controller.fetch_compatible_host_nodes(MIN_REQUIREMENTS, max_price)
    if not filtered_nodes:
        logger.error("No suitable host nodes found.")
        sys.exit(1)
    logger.info(f"Found {len(filtered_nodes)} suitable host nodes.")

    logger.info(f"Attempting {vm_type} VM deployment on the close host nodes...")
    comfyui_password = generate_strong_password() if not bare_vm else None
    node_info = controller.deploy_vm_on_tensordock(
        host_nodes=filtered_nodes,
        vm_name=vm_name,
        password=password,
        public_ssh_key=public_ssh_key,
        comfyui_password=comfyui_password,
        location=location,
        docker_image=docker_image,
        bare_vm=bare_vm,
    )
    if not node_info:
        vm_type = "ComfyStream" if not bare_vm else "bare"
        logger.error(f"Failed to deploy {vm_type} VM.")
        sys.exit(1)

    # Print access information.
    ssh_command, comfyui_url = get_vm_access_info(node_info)
    if not bare_vm:
        logger.info(
            f"{Fore.BLUE}Provisioning Comfystream and ComfyUI. This may take up to `"
            f"30 minutes.{Style.RESET_ALL}"
        )
        comfyui_username = "comfyadmin"
    else:
        comfyui_username, comfyui_url = None, None
    display_login_info(
        comfyui_url=comfyui_url,
        comfyui_username=comfyui_username,
        comfyui_password=comfyui_password,
        ssh_command=ssh_command,
    )
    if qr_code and comfyui_url:
        logger.info("Generating QR codes for easy access:")
        generate_qr_code(comfyui_url)
    logger.warning(
        "Remember to remove the VM after use to avoid unnecessary costs. Run "
        f"'spinup_comfystream_tensordock.py --delete {node_info['server']}' to remove "
        "the VM."
    )


if __name__ == "__main__":
    main()
