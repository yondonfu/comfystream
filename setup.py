from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "asyncio",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git",
    ],
    url="https://github.com/yondonfu/comfystream",
)
