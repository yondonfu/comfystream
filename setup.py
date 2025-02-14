from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "asyncio",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git@ce3583ad42c024b8f060d0002cbe20c265da6dc8",
    ],
    extras_require={"dev": ["pytest"]},
    url="https://github.com/yondonfu/comfystream",
)
