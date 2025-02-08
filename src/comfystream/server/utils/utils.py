"""General utility functions."""

import asyncio
import json
import random
import types
import logging
from aiohttp import web
import os
from pathlib import Path
import subprocess
import sys
import requests

from typing import List, Tuple
from contextlib import asynccontextmanager

from git import Repo

logger = logging.getLogger(__name__)


# Original issue: https://github.com/aiortc/aioice/pull/63
# Copied from: https://github.com/toverainc/willow-inference-server/pull/17/files
def patch_loop_datagram(local_ports: List[int]):
    loop = asyncio.get_event_loop()
    if getattr(loop, "_patch_done", False):
        return

    # Monkey patch aiortc to control ephemeral ports
    old_create_datagram_endpoint = loop.create_datagram_endpoint

    async def create_datagram_endpoint(
        self, protocol_factory, local_addr: Tuple[str, int] = None, **kwargs
    ):
        # if port is specified just use it
        if local_addr and local_addr[1]:
            return await old_create_datagram_endpoint(
                protocol_factory, local_addr=local_addr, **kwargs
            )
        if local_addr is None:
            return await old_create_datagram_endpoint(
                protocol_factory, local_addr=None, **kwargs
            )
        # if port is not specified make it use our range
        ports = list(local_ports)
        random.shuffle(ports)
        for port in ports:
            try:
                ret = await old_create_datagram_endpoint(
                    protocol_factory, local_addr=(local_addr[0], port), **kwargs
                )
                logger.debug(f"create_datagram_endpoint chose port {port}")
                return ret
            except OSError as exc:
                if port == ports[-1]:
                    # this was the last port, give up
                    raise exc
        raise ValueError("local_ports must not be empty")

    loop.create_datagram_endpoint = types.MethodType(create_datagram_endpoint, loop)
    loop._patch_done = True


def add_prefix_to_app_routes(app: web.Application, prefix: str):
    """Add a prefix to all routes in the given application.

    Args:
        app: The web application whose routes will be prefixed.
        prefix: The prefix to add to all routes.
    """
    prefix = prefix.rstrip("/")
    for route in list(app.router.routes()):
        new_path = prefix + route.resource.canonical
        app.router.add_route(route.method, new_path, route.handler)


@asynccontextmanager
async def temporary_log_level(logger_name: str, level: int):
    """Temporarily set the log level of a logger.

    Args:
        logger_name: The name of the logger to set the level for.
        level: The log level to set.
    """
    if level is not None:
        logger = logging.getLogger(logger_name)
        original_level = logger.level
        logger.setLevel(level)
    try:
        yield
    finally:
        if level is not None:
            logger.setLevel(original_level)
        
def list_nodes(workspace_dir):
    custom_nodes_path = Path(os.path.join(workspace_dir, "custom_nodes"))
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    os.chdir(custom_nodes_path)

    nodes = []
    for node in custom_nodes_path.iterdir():
        if node.is_dir():
            print(f"checking custom_node:{node.name}")
            repo = Repo(node)
            fetch_info = repo.remotes.origin.fetch(repo.active_branch.name)
            
            node_info = {
                "name": node.name,
                "url": repo.remotes.origin.url,
                "branch": repo.active_branch.name,
                "commit": repo.head.commit.hexsha[:7],
                "update_available": repo.head.commit.hexsha != fetch_info[0].commit.hexsha,
            }

            try:
                with open(node / "node_info.json") as f:
                    node_info.update(json.load(f))
            except FileNotFoundError:
                pass

            nodes.append(node_info)

    return nodes


def install_node(node, workspace_dir):
    custom_nodes_path = workspace_dir / "custom_nodes"
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    os.chdir(custom_nodes_path)

    try:
        dir_name = node_info['url'].split("/")[-1].replace(".git", "")
        node_path = custom_nodes_path / dir_name

        print(f"Installing {node_info['name']}...")

        # Clone the repository if it doesn't already exist
        if not node_path.exists():
            cmd = ["git", "clone", node_info['url']]
            if 'branch' in node_info:
                cmd.extend(["-b", node_info['branch']])
            subprocess.run(cmd, check=True)
        else:
            print(f"{node_info['name']} already exists, skipping clone.")

        # Checkout specific commit if branch is a commit hash
        if 'branch' in node_info and len(node_info['branch']) == 40:  # SHA-1 hash length
            subprocess.run(["git", "-C", dir_name, "checkout", node_info['branch']], check=True)

        # Install requirements if present
        requirements_file = node_path / "requirements.txt"
        if requirements_file.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], check=True)

        # Install additional dependencies if specified
        if 'dependencies' in node_info:
            for dep in node_info['dependencies']:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)

        print(f"Installed {node_info['name']}")
    except Exception as e:
        print(f"Error installing {node_info['name']} {e}")
        raise e
        return
