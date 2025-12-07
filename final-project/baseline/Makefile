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
	@kubectl cluster-info > /dev/null 2>&1 || (echo "❌ No Kubernetes cluster found. Please start a cluster first:" && echo "   - minikube start" && echo "   - kind create cluster" && exit 1)
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/db-deployment.yaml
	kubectl apply -f k8s/auth-deployment.yaml
	kubectl apply -f k8s/app-deployment.yaml
	kubectl apply -f k8s/ingress.yaml

k8s-delete:
	kubectl delete -f k8s/ingress.yaml || true
	kubectl delete -f k8s/app-deployment.yaml || true
	kubectl delete -f k8s/auth-deployment.yaml || true
	kubectl delete -f k8s/db-deployment.yaml || true
	kubectl delete -f k8s/namespace.yaml || true

k8s-load-images:
	@if command -v kind &> /dev/null && kind get clusters &> /dev/null 2>&1; then \
		echo "Loading images to kind cluster..."; \
		kind load docker-image db-service:latest; \
		kind load docker-image auth-service:latest; \
		kind load docker-image app-service:latest; \
	elif command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then \
		echo "Loading images to minikube cluster..."; \
		minikube image load db-service:latest; \
		minikube image load auth-service:latest; \
		minikube image load app-service:latest; \
	else \
		echo "⚠️  No local cluster detected. Images may need to be pushed to a registry."; \
	fi

# Full deployment workflow
deploy: build-all k8s-load-images k8s-deploy

clean:
	kubectl delete -f k8s/ || true
	docker rmi app-service:latest auth-service:latest db-service:latest || true

