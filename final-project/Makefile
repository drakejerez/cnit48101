.PHONY: build build-all deploy clean k8s-deploy k8s-delete k8s-load-images

# Build individual images
build-app:
	docker build -f Dockerfile.app -t app-service:latest .

build-auth:
	docker build -f Dockerfile.auth -t auth-service:latest .

build-db:
	docker build -f Dockerfile.db -t db-service:latest .

build-all: build-app build-auth build-db

# Kubernetes commands
k8s-deploy:
	@echo "Checking Kubernetes cluster connection..."
	@kubectl cluster-info > /dev/null 2>&1 || (echo "❌ No Kubernetes cluster found. Please set up kubeadm first:" && echo "   See KUBEADM-SETUP.md or run: sudo ./setup-kubeadm.sh" && exit 1)
	@echo "✅ Deploying to kubeadm cluster..."
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/otel-collector-config.yaml
	@kubectl apply -f k8s/jaeger-deployment.yaml
	@kubectl apply -f k8s/prometheus-deployment.yaml
	@kubectl apply -f k8s/db-deployment.yaml
	@kubectl apply -f k8s/auth-deployment.yaml
	@kubectl apply -f k8s/app-deployment.yaml
	@kubectl apply -f k8s/ingress.yaml
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "Access services:"
	@echo "  Jaeger UI: kubectl port-forward -n microservices svc/jaeger-query 16686:16686"
	@echo "  Prometheus: kubectl port-forward -n microservices svc/prometheus 9090:9090"

k8s-delete:
	@kubectl cluster-info > /dev/null 2>&1 || (echo "❌ No Kubernetes cluster found." && exit 1)
	@kubectl delete -f k8s/ || true

k8s-load-images:
	@kubectl cluster-info > /dev/null 2>&1 || (echo "❌ No Kubernetes cluster found. Set up kubeadm first." && exit 1)
	@echo "⚠️  For kubeadm, images need to be available on nodes."
	@echo "   Options:"
	@echo "   1. Build images on each node: docker build -t app-service:latest ."
	@echo "   2. Use a container registry and update imagePullPolicy"
	@echo "   3. Load images manually: docker save <image> | sudo ctr -n k8s.io images import -"
	@echo ""
	@echo "   Current manifests use imagePullPolicy: Never (expects local images)"

# Full deployment workflow
deploy: build-all k8s-load-images k8s-deploy

clean:
	@kubectl cluster-info > /dev/null 2>&1 && kubectl delete -f k8s/ || true
	@docker rmi app-service:latest auth-service:latest db-service:latest || true

