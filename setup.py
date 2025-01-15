from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "asyncio",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git@1f69d3ec0b95ff6512b5976752f33fc4c56a4fbe",
    ],
    extras_require={"dev": ["pytest"]},
    url="https://github.com/yondonfu/comfystream",
)
