FROM eliteencoder/comfyui-base:latest
ENV PATH="/miniconda3/bin:${PATH}"

# Remove RunPod logo, replace with Livepeer AI
RUN head -n $(($lines - 2)) ~/.bashrc > ~/.bashrc
RUN echo -e "echo -e '\nFor detailed documentation and guides, please visit:\n\033[1;34mhttps://pipelines.livepeer.org/docs\033[0m and \033[1;34mhttps://mirror.xyz.livepeer.eth/\033[0m\n\n'" >> /root/.bashrc

WORKDIR /
# Install NVM
ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 18.18.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Install node and npm
RUN source $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

# Add node and npm to path so the commands are available
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Create a symlink to the ComfyUI workspace
RUN ln -s /ComfyUI /workspace/ComfyUI
