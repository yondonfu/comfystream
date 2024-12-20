from setuptools import setup, find_packages

setup(
    name="comfystream",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "asyncio",
        # Pin opentelemetry versions until this comfyui PR is merged:
        # https://github.com/hiddenswitch/ComfyUI/pull/26
        "opentelemetry-distro==0.48b0",
        "opentelemetry-exporter-otlp==1.27.0",
        "opentelemetry-propagator-jaeger==1.27.0",
        "opentelemetry-instrumentation==0.48b0",
        "opentelemetry-util-http==0.48b0",
        "opentelemetry-instrumentation-aio-pika==0.48b0",
        "opentelemetry-instrumentation-requests==0.48b0",
        "opentelemetry-semantic-conventions==0.48b0",
        "comfyui @ git+https://github.com/hiddenswitch/ComfyUI.git@89d07f3adf32a6703181343bc732bd85104bb653",
    ],
    extras_require={"dev": ["pytest"]},
    url="https://github.com/yondonfu/comfystream",
)
