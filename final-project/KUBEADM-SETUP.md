# kubeadm Setup Guide

## Prerequisites

- Ubuntu 20.04+ or Debian-based system
- Root or sudo access
- At least 2 CPU cores and 2GB RAM (4GB+ recommended)
- Container runtime (containerd)

## Installation Steps

### 1. Disable Swap
```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

### 2. Load Kernel Modules
```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

### 3. Configure Kernel Parameters
```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### 4. Install containerd
```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install containerd
sudo apt-get update
sudo apt-get install -y containerd.io

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml

# Restart containerd
sudo systemctl restart containerd
sudo systemctl enable containerd
```

### 5. Install kubeadm, kubelet, kubectl
```bash
# Add Kubernetes GPG key (using new repository format)
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add Kubernetes repository (NEW format - old apt.kubernetes.io is deprecated)
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install Kubernetes components
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

**Note:** If you see errors about the old repository (`apt.kubernetes.io`), remove any old entries:
```bash
sudo rm -f /etc/apt/sources.list.d/kubernetes.list
sudo rm -f /usr/share/keyrings/kubernetes-archive-keyring.gpg
# Then re-run the installation steps above
```

### 6. Initialize Cluster (Master Node)

**For single-node cluster (master can schedule pods):**
```bash
sudo kubeadm init \
  --apiserver-advertise-address=$(hostname -I | awk '{print $1}') \
  --pod-network-cidr=192.168.0.0/16 \
  --ignore-preflight-errors=Swap

# Set up kubectl for your user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install Calico CNI
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/custom-resources.yaml

# Allow master node to schedule pods (for single-node setup)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# Wait for nodes to be ready
kubectl wait --for=condition=ready node --all --timeout=300s
```

**For multi-node cluster:**
```bash
# On master node
sudo kubeadm init \
  --apiserver-advertise-address=$(hostname -I | awk '{print $1}') \
  --pod-network-cidr=192.168.0.0/16

# Set up kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install Calico CNI
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/custom-resources.yaml

# Get join command for workers
kubeadm token create --print-join-command
```

### 7. Join Worker Nodes (Optional - for multi-node)

On each worker node, run the join command from step 6:
```bash
sudo kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

## Verify Installation

```bash
# Check cluster status
kubectl cluster-info

# Check nodes
kubectl get nodes

# Check all pods
kubectl get pods --all-namespaces
```

## Troubleshooting

### Reset cluster (if needed)
```bash
sudo kubeadm reset
sudo rm -rf /etc/cni/net.d
sudo rm -rf /var/lib/etcd
```

### Check kubelet status
```bash
sudo systemctl status kubelet
```

### View kubelet logs
```bash
sudo journalctl -xeu kubelet
```

## Quick Setup Script

Save this as `setup-kubeadm.sh` and run:
```bash
chmod +x setup-kubeadm.sh
sudo ./setup-kubeadm.sh
```

See `setup-kubeadm.sh` in this directory for a complete automated setup.

