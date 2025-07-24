#!/bin/bash
set -e

echo "=== Packaging OpenCV CUDA Build ==="

# Configuration
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
OPENCV_VERSION="${OPENCV_VERSION:-4.11.0}"
CUDA_ARCH_LIST="${CUDA_ARCH_LIST:-8.0+PTX}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# Create package directory
PACKAGE_DIR="$WORKSPACE_DIR/opencv-cuda-package"
mkdir -p "$PACKAGE_DIR"

echo "Creating OpenCV CUDA package..."

# Create directory structure
mkdir -p "$PACKAGE_DIR/cv2"
mkdir -p "$PACKAGE_DIR/lib"
mkdir -p "$PACKAGE_DIR/include"
mkdir -p "$PACKAGE_DIR/share"

# Copy Python cv2 package
echo "Packaging Python cv2 module..."
if [ -d "/usr/local/lib/python$PYTHON_VERSION/site-packages/cv2" ]; then
    cp -r "/usr/local/lib/python$PYTHON_VERSION/site-packages/cv2"/* "$PACKAGE_DIR/cv2/"
elif [ -d "/usr/local/lib/python$PYTHON_VERSION/dist-packages/cv2" ]; then
    cp -r "/usr/local/lib/python$PYTHON_VERSION/dist-packages/cv2"/* "$PACKAGE_DIR/cv2/"
else
    echo "⚠️  Warning: Could not find cv2 Python package"
fi

# Copy OpenCV libraries
echo "Packaging OpenCV libraries..."
if ls /usr/local/lib/libopencv_* >/dev/null 2>&1; then
    cp /usr/local/lib/libopencv_* "$PACKAGE_DIR/lib/"
else
    echo "⚠️  Warning: Could not find OpenCV libraries"
fi

# Copy headers
echo "Packaging OpenCV headers..."
if [ -d "/usr/local/include/opencv4" ]; then
    cp -r /usr/local/include/opencv4 "$PACKAGE_DIR/include/"
fi

# Copy pkgconfig files
echo "Packaging pkgconfig files..."
if [ -d "/usr/local/lib/pkgconfig" ]; then
    mkdir -p "$PACKAGE_DIR/lib/pkgconfig"
    cp /usr/local/lib/pkgconfig/opencv*.pc "$PACKAGE_DIR/lib/pkgconfig/" 2>/dev/null || true
fi

# Copy CMake files
echo "Packaging CMake configuration..."
if [ -d "/usr/local/lib/cmake/opencv4" ]; then
    mkdir -p "$PACKAGE_DIR/lib/cmake"
    cp -r /usr/local/lib/cmake/opencv4 "$PACKAGE_DIR/lib/cmake/"
fi

# Create build information file
echo "Creating build information..."
cat > "$PACKAGE_DIR/build_info.txt" << EOF
OpenCV CUDA Build Information
============================

Build Configuration:
- OpenCV Version: $OPENCV_VERSION
- CUDA Architecture: $CUDA_ARCH_LIST
- Python Version: $PYTHON_VERSION
- Build Date: $(date)
- Build Host: $(hostname)
- Git Commit: ${GITHUB_SHA:-unknown}
- Git Ref: ${GITHUB_REF:-unknown}

System Information:
- CUDA Version: $(nvcc --version | grep "release" | awk '{print $6}' | cut -c2- || echo "unknown")
- CMake Version: $(cmake --version | head -1 | awk '{print $3}' || echo "unknown")
- GCC Version: $(gcc --version | head -1 || echo "unknown")

Installation Paths:
- Libraries: /usr/local/lib
- Headers: /usr/local/include/opencv4
- Python Package: /usr/local/lib/python$PYTHON_VERSION/*/cv2

Verification:
$(python3 -c "
try:
    import cv2
    print(f'✅ OpenCV {cv2.__version__} imported successfully')
    cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
    print(f'✅ CUDA devices detected: {cuda_devices}')
    if cuda_devices > 0:
        print('✅ CUDA support verified')
    else:
        print('❌ No CUDA devices detected')
except Exception as e:
    print(f'❌ Import failed: {e}')
" 2>/dev/null || echo "❌ Verification failed")

Package Contents:
- cv2/: Python OpenCV module
- lib/: OpenCV shared libraries
- include/: OpenCV header files
- lib/pkgconfig/: pkg-config files
- lib/cmake/: CMake configuration files
EOF

# Create installation script
echo "Creating installation script..."
cat > "$PACKAGE_DIR/install.sh" << 'EOF'
#!/bin/bash
set -e

echo "=== OpenCV CUDA Installation Script ==="

PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
CONDA_ENV="${CONDA_ENV:-comfystream}"

# Detect installation target
if [ -d "/workspace/miniconda3/envs/$CONDA_ENV" ]; then
    SITE_PACKAGES_DIR="/workspace/miniconda3/envs/$CONDA_ENV/lib/python$PYTHON_VERSION/site-packages"
    echo "Installing to Conda environment: $CONDA_ENV"
else
    SITE_PACKAGES_DIR="/usr/local/lib/python$PYTHON_VERSION/site-packages"
    echo "Installing to system Python"
fi

# Install Python package
if [ -d "cv2" ]; then
    echo "Installing cv2 Python package..."
    rm -rf "$SITE_PACKAGES_DIR/cv2"*
    cp -r cv2 "$SITE_PACKAGES_DIR/"
    echo "✅ cv2 package installed"
fi

# Install libraries
if [ -d "lib" ] && ls lib/libopencv_* >/dev/null 2>&1; then
    echo "Installing OpenCV libraries..."
    cp lib/libopencv_* /usr/lib/x86_64-linux-gnu/ 2>/dev/null || cp lib/libopencv_* /usr/local/lib/
    ldconfig
    echo "✅ OpenCV libraries installed"
fi

# Install headers
if [ -d "include" ]; then
    echo "Installing OpenCV headers..."
    cp -r include/* /usr/local/include/
    echo "✅ OpenCV headers installed"
fi

# Install pkg-config files
if [ -d "lib/pkgconfig" ]; then
    echo "Installing pkg-config files..."
    cp lib/pkgconfig/*.pc /usr/local/lib/pkgconfig/ 2>/dev/null || true
    echo "✅ pkg-config files installed"
fi

# Install CMake files
if [ -d "lib/cmake" ]; then
    echo "Installing CMake configuration..."
    cp -r lib/cmake/* /usr/local/lib/cmake/
    echo "✅ CMake configuration installed"
fi

# Verify installation
echo "Verifying installation..."
python3 -c "
import cv2
print(f'OpenCV version: {cv2.__version__}')
cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
print(f'CUDA devices: {cuda_devices}')
if cuda_devices > 0:
    print('✅ OpenCV CUDA installation successful!')
else:
    print('⚠️  CUDA support may not be available')
"

echo "✅ Installation completed"
EOF

chmod +x "$PACKAGE_DIR/install.sh"

# Create the tarball
echo "Creating distribution archive..."
cd "$WORKSPACE_DIR"
tar -czf opencv-cuda-release.tar.gz -C opencv-cuda-package .

# Create checksums
echo "Generating checksums..."
sha256sum opencv-cuda-release.tar.gz > opencv-cuda-release.tar.gz.sha256
md5sum opencv-cuda-release.tar.gz > opencv-cuda-release.tar.gz.md5

# Display package information
echo "=== Package Information ==="
echo "Package file: opencv-cuda-release.tar.gz"
echo "Package size: $(ls -lh opencv-cuda-release.tar.gz | awk '{print $5}')"
echo "SHA256: $(cat opencv-cuda-release.tar.gz.sha256 | awk '{print $1}')"
echo "MD5: $(cat opencv-cuda-release.tar.gz.md5 | awk '{print $1}')"

# List package contents
echo ""
echo "Package contents:"
tar -tzf opencv-cuda-release.tar.gz | head -20
if [ $(tar -tzf opencv-cuda-release.tar.gz | wc -l) -gt 20 ]; then
    echo "... and $(( $(tar -tzf opencv-cuda-release.tar.gz | wc -l) - 20 )) more files"
fi

echo "✅ OpenCV CUDA package created successfully"