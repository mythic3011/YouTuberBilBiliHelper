.PHONY: help build run test clean docker-build docker-up docker-down dev lint fmt

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the Go binary
	go build -o video-api .

run: ## Run the application
	go run main.go

dev: ## Run with hot reload (requires air)
	air

test: ## Run tests
	go test -v -race -coverprofile=coverage.out ./...

test-coverage: test ## Run tests with coverage report
	go tool cover -html=coverage.out

lint: ## Run linters
	golangci-lint run

fmt: ## Format code
	go fmt ./...
	goimports -w .

clean: ## Clean build artifacts
	rm -f video-api
	rm -f coverage.out
	rm -rf tmp/

docker-build: ## Build Docker image
	docker build -t video-api-go:latest .

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## Show Docker Compose logs
	docker-compose logs -f

deps: ## Download dependencies
	go mod download
	go mod verify

tidy: ## Tidy dependencies
	go mod tidy

vet: ## Run go vet
	go vet ./...

all: fmt lint test build ## Run all checks and build
