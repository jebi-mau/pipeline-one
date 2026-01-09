#!/bin/bash
# ZED SDK 5.1 Installation Script
# For Ubuntu 22.04 with CUDA 12.x

set -e

echo "=== ZED SDK 5.1 Installation ==="
echo ""

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    echo "Warning: This script is optimized for Ubuntu"
fi

# Check for CUDA
if ! command -v nvcc &> /dev/null; then
    echo "Error: CUDA not found. Please install CUDA 12.x first."
    echo "Visit: https://developer.nvidia.com/cuda-downloads"
    exit 1
fi

CUDA_VERSION=$(nvcc --version | grep "release" | sed 's/.*release //' | cut -d',' -f1)
echo "CUDA Version: $CUDA_VERSION"

# ZED SDK download URL (update for latest version)
ZED_SDK_URL="https://download.stereolabs.com/zedsdk/5.1/cu124/ubuntu22"

# Download directory
DOWNLOAD_DIR="/tmp/zed_sdk"
mkdir -p "$DOWNLOAD_DIR"

echo ""
echo "Downloading ZED SDK 5.1..."
echo "URL: $ZED_SDK_URL"

# Download the installer
wget -O "$DOWNLOAD_DIR/zed_sdk.run" "$ZED_SDK_URL"

echo ""
echo "Making installer executable..."
chmod +x "$DOWNLOAD_DIR/zed_sdk.run"

echo ""
echo "Running ZED SDK installer..."
echo "Note: This may require sudo access and will prompt for options."
echo ""

# Run the installer
sudo "$DOWNLOAD_DIR/zed_sdk.run"

echo ""
echo "=== ZED SDK Installation Complete ==="
echo ""
echo "Please verify installation:"
echo "1. Check ZED SDK path: ls /usr/local/zed"
echo "2. Install pyzed: pip install pyzed"
echo "3. Test: python -c 'import pyzed.sl as sl; print(sl.Camera())'"
echo ""
