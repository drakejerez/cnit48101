#!/bin/bash
# Fix deprecated Kubernetes repository issue
# Run with sudo

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root or with sudo"
    exit 1
fi

echo "🔧 Fixing Kubernetes repository..."

# Remove old deprecated repository entries
echo "Removing old repository entries..."
rm -f /etc/apt/sources.list.d/kubernetes.list
rm -f /usr/share/keyrings/kubernetes-archive-keyring.gpg

# Add new repository format
K8S_VERSION="v1.28"
mkdir -p /etc/apt/keyrings

echo "Adding new Kubernetes repository..."
curl -fsSL https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_VERSION/deb/ /" > /etc/apt/sources.list.d/kubernetes.list

echo "Updating package list..."
apt-get update -qq

echo "✅ Repository fixed! You can now install kubeadm:"
echo "   sudo apt-get install -y kubelet kubeadm kubectl"
echo "   sudo apt-mark hold kubelet kubeadm kubectl"

