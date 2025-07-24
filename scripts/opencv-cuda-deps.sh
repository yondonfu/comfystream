#!/bin/bash
set -e

echo "=== Installing OpenCV CUDA Dependencies ==="

# Update package list
apt-get update

# Install system libraries required for compiling OpenCV
echo "Installing build dependencies..."
apt-get install -yqq --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libavresample-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev \
    libdc1394-22-dev \
    libxvidcore-dev \
    libx264-dev \
    libtbb2 \
    libtbb-dev \
    libgflags-dev \
    libgoogle-glog-dev \
    libavutil-dev \
    python3-dev \
    python3-numpy \
    libopencv-dev \
    libeigen3-dev \
    liblapack-dev \
    libopenblas-dev

# Install additional libraries for enhanced functionality
echo "Installing additional OpenCV dependencies..."
apt-get install -yqq --no-install-recommends \
    libv4l-dev \
    libxine2-dev \
    libfaac-dev \
    libmp3lame-dev \
    libtheora-dev \
    libvorbis-dev \
    libxvidcore-dev \
    libopencore-amrnb-dev \
    libopencore-amrwb-dev \
    libavresample-dev \
    x264 \
    v4l-utils \
    libprotobuf-dev \
    protobuf-compiler \
    libgoogle-glog-dev \
    libgflags-dev \
    libgphoto2-dev \
    libeigen3-dev \
    libhdf5-dev

# Clean up apt cache to reduce image size
echo "Cleaning up package cache..."
apt-get autoremove -y
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "✅ OpenCV CUDA dependencies installed successfully"