#!/bin/bash
set -e

# OpenCV CUDA Build Script
# Based on the updated script from comfystream-docs
# This script builds OpenCV with CUDA support for optimal performance

# Default configuration
OPENCV_VERSION="${OPENCV_VERSION:-4.11.0}"
CUDA_ARCH_LIST="${CUDA_ARCH_LIST:-8.0+PTX}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
BUILD_JOBS="${BUILD_JOBS:-$(nproc)}"

echo "=== OpenCV CUDA Build Script ==="
echo "OpenCV Version: $OPENCV_VERSION"
echo "CUDA Architecture: $CUDA_ARCH_LIST"
echo "Python Version: $PYTHON_VERSION"
echo "Workspace Directory: $WORKSPACE_DIR"
echo "Build Jobs: $BUILD_JOBS"
echo "================================"

# Change to workspace directory
cd "$WORKSPACE_DIR"

# Clone OpenCV repositories
echo "Cloning OpenCV repositories..."
if [ ! -d "opencv" ]; then
    git clone --depth 1 --branch "$OPENCV_VERSION" https://github.com/opencv/opencv.git
fi

if [ ! -d "opencv_contrib" ]; then
    git clone --depth 1 --branch "$OPENCV_VERSION" https://github.com/opencv/opencv_contrib.git
fi

# Create build directory
mkdir -p opencv/build

# Create a toolchain file with absolute path
echo "Creating custom toolchain file..."
cat > custom_toolchain.cmake << EOF
# Custom toolchain file to exclude Conda paths

# Set system compilers
set(CMAKE_C_COMPILER "/usr/bin/gcc")
set(CMAKE_CXX_COMPILER "/usr/bin/g++")

# Set system root directories
set(CMAKE_FIND_ROOT_PATH "/usr")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Explicitly exclude Conda paths if they exist
list(APPEND CMAKE_IGNORE_PATH
    "$WORKSPACE_DIR/miniconda3"
    "$WORKSPACE_DIR/miniconda3/envs"
    "$WORKSPACE_DIR/miniconda3/envs/comfystream"
    "$WORKSPACE_DIR/miniconda3/envs/comfystream/lib"
)

# Set RPATH settings
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
set(CMAKE_INSTALL_RPATH "/usr/local/lib:/usr/lib/x86_64-linux-gnu")
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

# Python configuration for Conda environment if it exists
if(EXISTS "$WORKSPACE_DIR/miniconda3/envs/comfystream")
    set(PYTHON_LIBRARY "$WORKSPACE_DIR/miniconda3/envs/comfystream/lib/")
endif()
EOF

# Set environment variables for OpenCV
echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc || true

# Detect Python configuration
PYTHON_EXECUTABLE=""
PYTHON_INCLUDE_DIR=""
PYTHON_LIBRARY=""

if [ -f "$WORKSPACE_DIR/miniconda3/envs/comfystream/bin/python$PYTHON_VERSION" ]; then
    # Use Conda environment if available
    PYTHON_EXECUTABLE="$WORKSPACE_DIR/miniconda3/envs/comfystream/bin/python$PYTHON_VERSION"
    PYTHON_INCLUDE_DIR="$WORKSPACE_DIR/miniconda3/envs/comfystream/include/python$PYTHON_VERSION"
    PYTHON_LIBRARY="$WORKSPACE_DIR/miniconda3/envs/comfystream/lib/libpython$PYTHON_VERSION.so"
    echo "Using Conda Python environment"
else
    # Use system Python
    PYTHON_EXECUTABLE="/usr/bin/python3"
    PYTHON_INCLUDE_DIR="/usr/include/python$PYTHON_VERSION"
    PYTHON_LIBRARY="/usr/lib/x86_64-linux-gnu/libpython$PYTHON_VERSION.so"
    echo "Using system Python"
fi

echo "Python Configuration:"
echo "  Executable: $PYTHON_EXECUTABLE"
echo "  Include Dir: $PYTHON_INCLUDE_DIR"
echo "  Library: $PYTHON_LIBRARY"

# Build and install OpenCV with CUDA support
echo "Configuring OpenCV build..."
cd opencv/build
cmake \
  -D CMAKE_TOOLCHAIN_FILE="$WORKSPACE_DIR/custom_toolchain.cmake" \
  -D CMAKE_BUILD_TYPE=RELEASE \
  -D CMAKE_INSTALL_PREFIX=/usr/local \
  -D WITH_CUDA=ON \
  -D WITH_CUDNN=ON \
  -D WITH_CUBLAS=ON \
  -D WITH_TBB=ON \
  -D CUDA_ARCH_LIST="$CUDA_ARCH_LIST" \
  -D OPENCV_DNN_CUDA=ON \
  -D OPENCV_ENABLE_NONFREE=ON \
  -D CUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda \
  -D OPENCV_EXTRA_MODULES_PATH="$WORKSPACE_DIR/opencv_contrib/modules" \
  -D PYTHON3_EXECUTABLE="$PYTHON_EXECUTABLE" \
  -D PYTHON_INCLUDE_DIR="$PYTHON_INCLUDE_DIR" \
  -D PYTHON_LIBRARY="$PYTHON_LIBRARY" \
  -D HAVE_opencv_python3=ON \
  -D WITH_NVCUVID=OFF \
  -D WITH_NVCUVENC=OFF \
  -D BUILD_EXAMPLES=OFF \
  -D BUILD_TESTS=OFF \
  -D BUILD_PERF_TESTS=OFF \
  -D BUILD_opencv_apps=OFF \
  -D BUILD_SHARED_LIBS=ON \
  -D WITH_OPENGL=ON \
  -D WITH_OPENCL=ON \
  -D WITH_IPP=ON \
  -D WITH_TBB=ON \
  -D WITH_EIGEN=ON \
  -D WITH_V4L=ON \
  -D BUILD_NEW_PYTHON_SUPPORT=ON \
  -D OPENCV_SKIP_PYTHON_LOADER=ON \
  -D OPENCV_GENERATE_PKGCONFIG=ON \
  ..

echo "Building OpenCV (this may take a while)..."
make -j"$BUILD_JOBS"

echo "Installing OpenCV..."
make install
ldconfig

# Verify installation
echo "Verifying OpenCV CUDA installation..."
if command -v python3 &> /dev/null; then
    python3 -c "
import cv2
print(f'OpenCV version: {cv2.__version__}')
cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
print(f'CUDA devices: {cuda_devices}')
if cuda_devices > 0:
    print('✅ OpenCV CUDA installation successful!')
else:
    print('❌ CUDA support not detected')
    exit(1)
" || echo "⚠️  Verification failed - you may need to configure your environment"
fi

# Create installation summary
echo "=== Installation Summary ==="
echo "OpenCV version: $OPENCV_VERSION"
echo "Installation path: /usr/local"
echo "Python packages: $(find /usr/local/lib/python*/*/cv2 -name "*.so" 2>/dev/null | head -3)"
echo "OpenCV libraries: $(find /usr/local/lib -name "libopencv_*.so" 2>/dev/null | wc -l) libraries installed"
echo "============================"

echo "OpenCV CUDA build completed successfully!"