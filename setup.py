from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "torch==2.4.1+cu121",
        "torchvision",
        "torchaudio==2.4.1+cu121",
        "xformers==0.0.28.post1",
        "asyncio",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git",
    ],
    dependency_links=[
        "https://download.pytorch.org/whl/cu121",
        "https://download.pytorch.org/whl/",
    ],
    url="https://github.com/yondonfu/comfystream",
)
