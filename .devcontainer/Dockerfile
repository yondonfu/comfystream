# FROM comfyui-builder:custom-nodes
FROM comfystream:base

WORKDIR /workspaces/comfystream
RUN eval "$(/root/miniconda3/bin/conda shell.bash hook)"
ENV PATH="/root/miniconda3/bin:${PATH}"
RUN conda init bash

# Switch env back to base
RUN conda config --set auto_activate_base false
RUN /bin/bash -c "source ~/.bashrc"
# RUN python main.py --listen

