#!/bin/bash

# Initialize conda if needed
if ! command -v conda &> /dev/null; then
    /miniconda3/bin/conda init bash
fi

cd /workspace/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps   
fi
if [ ! -d ".env" ]; then
    echo "NEXT_PUBLIC_DEFAULT_STREAM_URL=http://127.0.0.1:8889" > .env
fi

cd /workspace
/bin/bash