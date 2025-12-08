#!/bin/bash
# Initialize kubeadm Kubernetes cluster
# Assumes kubeadm, kubelet, kubectl, and containerd are already installed
# Run with sudo

set -e

echo "🚀 Initializing kubeadm Kubernetes cluster..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root or with sudo"
    exit 1
fi

# Check if kubeadm is installed
if ! command -v kubeadm &> /dev/null; then
    echo "❌ kubeadm is not installed"
    echo "   Install it first, then run this script"
    exit 1
fi

# Check if cluster already exists
if [ -f /etc/kubernetes/admin.conf ]; then
    echo "⚠️  Cluster already initialized!"
    echo "   To reset: sudo kubeadm reset"
    exit 1
fi

# Initialize cluster
echo "🚀 Initializing Kubernetes cluster..."
MASTER_IP=$(hostname -I | awk '{print $1}')

kubeadm init \
  --apiserver-advertise-address=$MASTER_IP \
  --pod-network-cidr=192.168.0.0/16 \
  --ignore-preflight-errors=Swap

# Set up kubectl for root user
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config

# Set up kubectl for regular user if exists
if [ -n "$SUDO_USER" ]; then
    mkdir -p /home/$SUDO_USER/.kube
    cp -i /etc/kubernetes/admin.conf /home/$SUDO_USER/.kube/config
    chown -R $SUDO_USER:$SUDO_USER /home/$SUDO_USER/.kube
    echo "✅ kubectl configured for user: $SUDO_USER"
fi

# Install Calico CNI
echo "📦 Installing Calico CNI..."
export KUBECONFIG=/etc/kubernetes/admin.conf
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml > /dev/null 2>&1
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/custom-resources.yaml > /dev/null 2>&1

# Allow master node to schedule pods (single-node setup)
echo "🔓 Allowing master node to schedule pods..."
kubectl taint nodes --all node-role.kubernetes.io/control-plane- > /dev/null 2>&1

# Wait for nodes to be ready
echo "⏳ Waiting for cluster to be ready..."
sleep 10
kubectl wait --for=condition=ready node --all --timeout=300s > /dev/null 2>&1 || true

echo ""
echo "✅ Kubernetes cluster initialized!"
echo ""
echo "To use kubectl:"
if [ -n "$SUDO_USER" ]; then
    echo "  export KUBECONFIG=/home/$SUDO_USER/.kube/config"
else
    echo "  export KUBECONFIG=/root/.kube/config"
fi
echo ""
echo "Check cluster status:"
echo "  kubectl cluster-info"
echo "  kubectl get nodes"
echo ""
echo "To join worker nodes, run on master:"
echo "  kubeadm token create --print-join-command"

