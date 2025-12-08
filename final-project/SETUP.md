# Setup Requirements

## Prerequisites

- **Docker**: Container runtime
- **Kubernetes**: Cluster (MicroK8s recommended for Ubuntu)
- **kubectl**: Kubernetes CLI
- **Python 3**: For traffic generator

## Ubuntu Installation

### Docker
```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in for group changes
```

### Kubernetes - MicroK8s (Recommended for Ubuntu)
```bash
sudo snap install microk8s --classic
sudo usermod -aG microk8s $USER
sudo chown -f -R $USER ~/.kube
# Log out and back in, then:
microk8s status --wait-ready
microk8s enable dns storage
alias kubectl='microk8s kubectl'
```

### Alternative: k3s
```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes
alias kubectl='sudo k3s kubectl'
```

### kubectl (if not using MicroK8s/k3s)
```bash
sudo snap install kubectl --classic
# Or:
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/
```

### Python
```bash
sudo apt-get install -y python3 python3-pip
pip3 install requests
```

## Verify
```bash
docker --version
kubectl version --client
python3 --version
microk8s status  # if using MicroK8s
```

