# Project Structure

## Architecture Pattern

Standard Go project layout following internal package conventions with clean separation of concerns.

## Directory Organization

```
.
├── main.go                    # Application entry point, server setup, graceful shutdown
├── internal/                  # Private application code (not importable by other projects)
│   ├── config/               # Configuration management (env vars)
│   ├── models/               # Data structures and DTOs
│   ├── services/             # Business logic layer
│   │   ├── redis.go         # Redis caching service
│   │   ├── video.go         # Video extraction via yt-dlp
│   │   ├── streaming.go     # Stream handling and proxying
│   │   └── system.go        # Health checks and metrics
│   └── api/                  # HTTP layer
│       ├── handlers.go      # HTTP request handlers
│       ├── routes.go        # Route registration
│       └── middleware.go    # HTTP middleware (CORS, logging, etc.)
├── docs/                      # Auto-generated Swagger documentation
├── cmd/                       # Additional command-line tools (if any)
├── deployments/              # Deployment configurations
└── tmp/                       # Build artifacts (gitignored)
```

## Code Organization Principles

### Layer Separation

1. **main.go**: Bootstrap, dependency injection, server lifecycle
2. **internal/config**: Configuration loading from environment
3. **internal/models**: Shared data structures (no business logic)
4. **internal/services**: Business logic, external integrations (yt-dlp, Redis)
5. **internal/api**: HTTP concerns only (handlers, routing, middleware)

### Service Layer Pattern

Services are initialized in main.go and injected into handlers:

- Each service has a clear responsibility
- Services can depend on other services
- Services receive config and logger via constructor

### Handler Pattern

- Handlers are methods on a Handler struct
- Handler struct holds service dependencies
- Handlers focus on HTTP concerns (parsing, validation, response formatting)
- Business logic delegated to services

## Naming Conventions

- **Packages**: lowercase, single word (config, models, services, api)
- **Files**: lowercase with underscores for multi-word (redis_test.go)
- **Structs**: PascalCase (VideoService, Config)
- **Functions/Methods**: PascalCase for exported, camelCase for private
- **Constants**: PascalCase or SCREAMING_SNAKE_CASE for env vars

## Testing

- Test files alongside source: `service_test.go` next to `service.go`
- Use table-driven tests where appropriate
- Mock external dependencies (Redis, yt-dlp)

## Adding New Features

1. Define models in `internal/models/`
2. Implement business logic in `internal/services/`
3. Add HTTP handlers in `internal/api/handlers.go`
4. Register routes in `internal/api/routes.go`
5. Update Swagger comments for documentation

## Import Path

Module name: `video-streaming-api`
Internal imports: `video-streaming-api/internal/...`
