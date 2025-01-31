FROM livepeerci/comfyui-base:latest
ENV PATH="/miniconda3/bin:${PATH}"
EXPOSE 8188
EXPOSE 8888
EXPOSE 3000
EXPOSE 1024-65535/udp

WORKDIR /

# Install NVM
ENV NVM_DIR=/root/.nvm
ENV NODE_VERSION=18.18.0
RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Install node and npm
RUN bash -c "source $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default"

# Add node and npm to path so the commands are available
ENV NODE_PATH=$NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH=$NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
RUN conda init bash