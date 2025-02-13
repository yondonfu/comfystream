from pathlib import Path
import os
import json
from git import Repo
import logging
import subprocess
import sys
import shutil

logger = logging.getLogger(__name__)

async def list_nodes(workspace_dir):
    custom_nodes_path = Path(os.path.join(workspace_dir, "custom_nodes"))
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    os.chdir(custom_nodes_path)
    
    nodes = []
    for node in custom_nodes_path.iterdir():
        if node.name == "__pycache__":
            continue
        
        if node.is_dir():
            logger.info(f"getting info for node: { node.name}")
            node_info = {
                "name": node.name,
                "version": "unknown",
                "url": "unknown",
                "branch": "unknown",
                "commit": "unknown",
                "update_available": "unknown",
            }

            #include VERSION if set in file
            version_file = os.path.join(custom_nodes_path, node.name, "VERSION")
            if os.path.exists(version_file):
                node_info["version"] = json.dumps(open(version_file).readline().strip())

            #include git info if available
            try:
                repo = Repo(node)
                node_info["url"] = repo.remotes.origin.url.replace(".git","")
                node_info["commit"] = repo.head.commit.hexsha[:7]
                if not repo.head.is_detached:
                    node_info["branch"] = repo.active_branch.name
                    fetch_info = repo.remotes.origin.fetch(repo.active_branch.name)
                    node_info["update_available"] = repo.head.commit.hexsha[:7] != fetch_info[0].commit.hexsha[:7]
                else:
                    node_info["branch"] = "detached"
  
            except Exception as e:
                logger.info(f"error getting repo info for {node.name}  {e}")
                
            nodes.append(node_info)
    
    return nodes

async def install_node(node, workspace_dir):
    '''
    install ComfyUI custom node in git repository.

    installs requirements.txt from repository if present
    
    # Paramaters
    url: url of the git repository
    branch: branch to install
    dependencies: comma separated list of pip dependencies to install
    '''

    custom_nodes_path = Path(os.path.join(workspace_dir, "custom_nodes"))
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    os.chdir(custom_nodes_path)
    node_url = node.get("url", "")
    if node_url == "":
        raise ValueError("url is required")
    
    if not ".git" in node_url:
        node_url = f"{node_url}.git"
    
    try:
        dir_name = node_url.split("/")[-1].replace(".git", "")
        node_path = custom_nodes_path / dir_name
        if not node_path.exists():
            # Clone and install the repository if it doesn't already exist
            logger.info(f"installing {dir_name}...")
            repo = Repo.clone_from(node["url"], node_path, depth=1)
            if "branch" in node:
                repo.git.checkout(node['branch'])
        else:
            # Update the repository if it already exists
            logger.info(f"updating node {dir_name}")
            repo = Repo(node_path)
            repo.remotes.origin.fetch()
            branch = node.get("branch",  repo.remotes.origin.refs[0].remote_head)

            repo.remotes.origin.pull(branch)
        
        # Install requirements if present
        requirements_file = node_path / "requirements.txt"
        if requirements_file.exists():
            subprocess.run(["conda", "run", "-n", "comfystream", "pip", "install", "-r", str(requirements_file)], check=True)
            subprocess.run(["conda", "run", "-n", "comfyui", "pip", "install", "-r", str(requirements_file)], check=True)

        # Install additional dependencies if specified
        if "dependencies" in node:
            for dep in node["dependencies"].split(','):
                subprocess.run(["conda", "run", "-n", "comfystream", "pip", "install", dep.strip()], check=True)
                subprocess.run(["conda", "run", "-n", "comfyui", "pip", "install", dep.strip()], check=True)

    except Exception as e:
        logger.error(f"Error installing {dir_name} {e}")
        raise e

async def delete_node(node, workspace_dir):
    custom_nodes_path = Path(os.path.join(workspace_dir, "custom_nodes"))
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    os.chdir(custom_nodes_path)
    if "name" not in node: 
        raise ValueError("name is required")
    
    node_path = custom_nodes_path / node["name"]
    if not node_path.exists():
        raise ValueError(f"node {node['name']} does not exist")
    try:
        #delete the folder and all its contents.  ignore_errors allows readonly files to be deleted
        logger.info(f"deleting node {node['name']}")
        shutil.rmtree(node_path, ignore_errors=True)
    except Exception as e:
        logger.error(f"error deleting node {node['name']}")
        raise Exception(f"error deleting node: {e}")


from comfy.nodes.package import ExportedNodes
from comfy.nodes.package import _comfy_nodes, _import_and_enumerate_nodes_in_module
from functools import reduce
from importlib.metadata import entry_points
import types

def force_import_all_nodes_in_workspace(vanilla_custom_nodes=True, raise_on_failure=False) -> ExportedNodes:
    # now actually import the nodes, to improve control of node loading order
    from comfy_extras import nodes as comfy_extras_nodes  # pylint: disable=absolute-import-used
    from comfy.cli_args import args
    from comfy.nodes import base_nodes
    from comfy.nodes.vanilla_node_importing import mitigated_import_of_vanilla_custom_nodes

    # only load these nodes once

    base_and_extra = reduce(lambda x, y: x.update(y),
                            map(lambda module_inner: _import_and_enumerate_nodes_in_module(module_inner, raise_on_failure=raise_on_failure), [
                                # this is the list of default nodes to import
                                base_nodes,
                                comfy_extras_nodes
                            ]),
                            ExportedNodes())
    custom_nodes_mappings = ExportedNodes()

    if args.disable_all_custom_nodes:
        logging.info("Loading custom nodes was disabled, only base and extra nodes were loaded")
        _comfy_nodes.update(base_and_extra)
        return _comfy_nodes

    # load from entrypoints
    for entry_point in entry_points().select(group='comfyui.custom_nodes'):
        # Load the module associated with the current entry point
        try:
            module = entry_point.load()
        except ModuleNotFoundError as module_not_found_error:
            logging.error(f"A module was not found while importing nodes via an entry point: {entry_point}. Please ensure the entry point in setup.py is named correctly", exc_info=module_not_found_error)
            continue

        # Ensure that what we've loaded is indeed a module
        if isinstance(module, types.ModuleType):
            custom_nodes_mappings.update(
                _import_and_enumerate_nodes_in_module(module, print_import_times=True))

    # load the vanilla custom nodes last
    if vanilla_custom_nodes:
        custom_nodes_mappings += mitigated_import_of_vanilla_custom_nodes()

    # don't allow custom nodes to overwrite base nodes
    custom_nodes_mappings -= base_and_extra

    _comfy_nodes.update(base_and_extra + custom_nodes_mappings)
    
    return _comfy_nodes

