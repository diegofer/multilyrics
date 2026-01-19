#!/usr/bin/env bash
# MultiLyrics - Linux Dependencies Setup Script
# Automatically installs required system dependencies for Linux

set -e  # Exit on error

echo "=================================================="
echo "MultiLyrics - Linux Dependencies Setup"
echo "=================================================="
echo ""

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "❌ Cannot detect Linux distribution"
    exit 1
fi

echo "🐧 Detected distribution: $DISTRO"
echo ""

# Function to check if libxcb-cursor0 is installed
check_libxcb() {
    if ldconfig -p | grep -q libxcb-cursor.so.0; then
        return 0  # Installed
    else
        return 1  # Not installed
    fi
}

# Check current status
echo "🔍 Checking libxcb-cursor0..."
if check_libxcb; then
    echo "✅ libxcb-cursor0 is already installed"
    exit 0
fi

echo "⚠️  libxcb-cursor0 is NOT installed"
echo "📦 This library is required for proper modal dialog rendering on Wayland"
echo ""

# Install based on distribution
case "$DISTRO" in
    ubuntu|debian|linuxmint|pop)
        echo "🔧 Installing libxcb-cursor0 (Ubuntu/Debian)..."
        sudo apt update
        sudo apt install -y libxcb-cursor0
        ;;

    fedora|rhel|centos)
        echo "🔧 Installing libxcb-cursor (Fedora/RHEL)..."
        sudo dnf install -y libxcb-cursor
        ;;

    arch|manjaro)
        echo "🔧 Installing libxcb (Arch)..."
        sudo pacman -S --noconfirm libxcb
        ;;

    opensuse*)
        echo "🔧 Installing libxcb-cursor0 (openSUSE)..."
        sudo zypper install -y libxcb-cursor0
        ;;

    *)
        echo "❌ Unsupported distribution: $DISTRO"
        echo "💡 Please install libxcb-cursor0 manually:"
        echo ""
        echo "   Ubuntu/Debian: sudo apt install libxcb-cursor0"
        echo "   Fedora:        sudo dnf install libxcb-cursor"
        echo "   Arch:          sudo pacman -S libxcb"
        exit 1
        ;;
esac

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if check_libxcb; then
    echo "✅ libxcb-cursor0 installed successfully!"
    echo ""
    echo "=================================================="
    echo "✅ All dependencies installed!"
    echo "=================================================="
    exit 0
else
    echo "❌ Installation failed. Please install manually."
    exit 1
fi
