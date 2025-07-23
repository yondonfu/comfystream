# OpenCV CUDA Build Documentation

This document describes the improved OpenCV CUDA build process for ComfyStream, including the new GitHub workflow that automatically builds and produces artifacts.

## Overview

The OpenCV CUDA build system has been updated with the following improvements:

- **Automated GitHub workflow** for building OpenCV with CUDA support
- **Updated build script** based on the latest best practices from the documentation
- **Artifact generation** for easy distribution and deployment
- **Fallback mechanism** between prebuilt packages and source builds
- **Better error handling** and verification

## GitHub Workflow

The new `.github/workflows/opencv-cuda-build.yaml` workflow provides:

### Triggers
- **Push to main** (when build-related files change)
- **Pull requests** (for testing changes)
- **Manual dispatch** (with configurable parameters)

### Features
- Builds OpenCV 4.11.0 with CUDA support by default
- Configurable OpenCV version and CUDA architecture
- Runs on self-hosted GPU runners
- Produces downloadable artifacts
- Creates GitHub releases for tagged versions

### Manual Execution
You can manually trigger the workflow with custom parameters:

1. Go to Actions tab in GitHub
2. Select "Build OpenCV with CUDA Support"
3. Click "Run workflow"
4. Configure parameters:
   - `opencv_version`: OpenCV version to build (default: 4.11.0)
   - `cuda_arch`: CUDA architecture (default: 8.0+PTX)

## Build Script Updates

The new `docker/opencv-build.sh` script includes:

### Improvements from Documentation
- **Better dependency management** with comprehensive system packages
- **Flexible Python detection** (Conda environment or system Python)
- **Enhanced CMake configuration** with optimized build flags
- **Improved toolchain file** to avoid Conda conflicts
- **Verification step** to ensure CUDA support is working
- **Detailed logging** and progress information

### Configuration Options
Environment variables you can set:

```bash
export OPENCV_VERSION="4.11.0"      # OpenCV version
export CUDA_ARCH_LIST="8.0+PTX"     # CUDA architectures
export PYTHON_VERSION="3.11"        # Python version
export WORKSPACE_DIR="/workspace"   # Build workspace
export BUILD_JOBS="$(nproc)"        # Parallel build jobs
```

## Integration with Existing System

### Entrypoint Script Updates
The `docker/entrypoint.sh` has been updated to:

1. **Try downloading** prebuilt packages first (fast)
2. **Fallback to building** from source if download fails
3. **Better error handling** and verification
4. **Maintain backward compatibility** with existing structure

### Usage in Docker
The existing Docker build process remains the same:

```dockerfile
# In Dockerfile.base
RUN conda run -n comfystream --no-capture-output bash /workspace/comfystream/docker/entrypoint.sh --opencv-cuda
```

## Verification

After installation, the system automatically verifies:

```python
import cv2
print(f'OpenCV version: {cv2.__version__}')
print(f'CUDA devices: {cv2.cuda.getCudaEnabledDeviceCount()}')
```

Expected output should show:
- OpenCV version 4.11.0 (or configured version)
- CUDA devices count > 0

## Artifacts

The workflow produces artifacts containing:

### Structure
```
opencv-cuda-release.tar.gz
├── cv2/                    # Python OpenCV package
├── lib/                    # OpenCV libraries
└── build_info.txt         # Build metadata
```

### Usage
Download and extract the artifact, then use with the existing installation process.

## Troubleshooting

### Common Issues

1. **CUDA not detected**: Ensure NVIDIA drivers and CUDA toolkit are properly installed
2. **Build failures**: Check system dependencies and available disk space
3. **Python import errors**: Verify Python environment and library paths

### Debug Mode
For detailed debugging, run the build script manually:

```bash
cd /workspace
export WORKSPACE_DIR="/workspace"
bash docker/opencv-build.sh
```

## Migration from Previous Version

The new system is backward compatible. Existing setups will:

1. Continue using prebuilt packages if available
2. Automatically fallback to the improved build process
3. Maintain the same API and installation paths

## Performance Benefits

The updated build includes:

- **Optimized CUDA architectures** for better GPU utilization
- **Enhanced DNN support** with CUDA acceleration
- **Better memory management** with improved RPATH settings
- **Reduced build conflicts** through toolchain isolation

## Future Improvements

Planned enhancements include:

- Multi-architecture builds (ARM64 support)
- Cached build artifacts for faster CI/CD
- Integration with package managers
- Automated performance benchmarking