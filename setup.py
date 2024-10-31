from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "asyncio",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git@89d07f3adf32a6703181343bc732bd85104bb653",
    ],
    url="https://github.com/yondonfu/comfystream",
)
