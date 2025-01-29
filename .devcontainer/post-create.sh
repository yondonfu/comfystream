#!/bin/bash

# Initialize conda if needed
if ! command -v conda &> /dev/null; then
    /miniconda3/bin/conda init bash
fi

cd /workspace/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps   
fi

cd /workspace
/bin/bash