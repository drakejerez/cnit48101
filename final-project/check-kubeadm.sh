#!/bin/bash
# Check kubeadm cluster status

echo "🔍 Checking Kubernetes cluster status..."
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    echo "   Install it as part of kubeadm setup: sudo ./setup-kubeadm.sh"
    exit 1
fi
echo "✅ kubectl is installed"

# Check KUBECONFIG
if [ -z "$KUBECONFIG" ]; then
    if [ -f "$HOME/.kube/config" ]; then
        export KUBECONFIG="$HOME/.kube/config"
        echo "✅ Found kubeconfig at: $HOME/.kube/config"
    elif [ -f "/root/.kube/config" ]; then
        export KUBECONFIG="/root/.kube/config"
        echo "✅ Found kubeconfig at: /root/.kube/config"
    elif [ -f "/etc/kubernetes/admin.conf" ]; then
        export KUBECONFIG="/etc/kubernetes/admin.conf"
        echo "✅ Found kubeconfig at: /etc/kubernetes/admin.conf"
    else
        echo "❌ No kubeconfig found"
        echo "   Expected locations:"
        echo "     - $HOME/.kube/config"
        echo "     - /root/.kube/config"
        echo "     - /etc/kubernetes/admin.conf"
        echo ""
        echo "   If you just ran setup-kubeadm.sh, try:"
        echo "     export KUBECONFIG=\$HOME/.kube/config"
        echo "     # or"
        echo "     export KUBECONFIG=/etc/kubernetes/admin.conf"
        exit 1
    fi
else
    echo "✅ KUBECONFIG is set to: $KUBECONFIG"
fi

# Check cluster connection
echo ""
echo "Testing cluster connection..."
if kubectl cluster-info &> /dev/null; then
    echo "✅ Cluster is accessible!"
    echo ""
    kubectl cluster-info
    echo ""
    kubectl get nodes
else
    echo "❌ Cannot connect to cluster"
    echo ""
    echo "Possible issues:"
    echo "  1. Cluster not initialized - Run: sudo ./setup-kubeadm.sh"
    echo "  2. kubeconfig not set - Run: export KUBECONFIG=\$HOME/.kube/config"
    echo "  3. Cluster not running - Check: sudo systemctl status kubelet"
    echo ""
    echo "Current KUBECONFIG: ${KUBECONFIG:-not set}"
    exit 1
fi

