# FastAPI Auth Service

A production-ready authentication microservice built with FastAPI, PostgreSQL, Redis, and JWT.

## Features

- User registration and login with JWT tokens
- Access token + refresh token flow
- Password hashing with bcrypt
- Rate limiting middleware (sliding-window via Redis)
- Async SQLAlchemy 2.0 with PostgreSQL
- Redis for token blacklisting and rate limiting
- Database migrations with Alembic
- Role-based access control (superuser vs. regular user)
- Comprehensive pytest test suite with async SQLite in-memory DB
- Multi-stage Docker build (non-root user, health check)
- Docker Compose with PostgreSQL and Redis
- CI/CD with GitHub Actions

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI 0.115 |
| Language | Python 3.12 |
| Database | PostgreSQL 15 (asyncpg driver) |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Caching / Blocklist | Redis 7 |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT), passlib (bcrypt) |
| Testing | pytest, pytest-asyncio, httpx |
| Containerisation | Docker, Docker Compose |
| CI | GitHub Actions |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/shahabRDZ/fastapi-auth-service.git
cd fastapi-auth-service

# Copy and edit environment variables
cp .env.example .env

# Start all services with Docker Compose
docker-compose up -d

# The API is now available at http://localhost:8000
# Interactive docs:  http://localhost:8000/docs
# ReDoc:             http://localhost:8000/redoc
```

## Running Locally (without Docker)

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set env vars (edit .env first)
cp .env.example .env

# Apply database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload
```

## API Endpoints

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | — | Register a new user |
| POST | `/api/v1/auth/login` | — | Obtain access + refresh tokens |
| POST | `/api/v1/auth/refresh` | — | Exchange refresh token for new pair |
| POST | `/api/v1/auth/logout` | Bearer | Revoke current access token |
| GET | `/api/v1/auth/me` | Bearer | Get authenticated user's profile |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/users/` | Superuser | List all users (paginated) |
| GET | `/api/v1/users/me` | Bearer | Get current user's full profile |
| PATCH | `/api/v1/users/me` | Bearer | Update current user's profile |
| POST | `/api/v1/users/me/change-password` | Bearer | Change password |
| GET | `/api/v1/users/{id}` | Superuser | Get user by UUID |
| DELETE | `/api/v1/users/{id}` | Superuser | Deactivate a user account |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Project Structure

```
fastapi-auth-service/
├── app/
│   ├── main.py           # Application factory, lifespan, middleware wiring
│   ├── config.py         # Pydantic Settings (reads from .env)
│   ├── database.py       # Async SQLAlchemy engine and session factory
│   ├── dependencies.py   # FastAPI dependency injection (auth, DB, Redis)
│   ├── middleware.py      # Sliding-window rate limiting via Redis
│   ├── models/
│   │   └── user.py       # SQLAlchemy ORM model
│   ├── schemas/
│   │   └── user.py       # Pydantic request / response schemas
│   ├── routers/
│   │   ├── auth.py       # /auth/* endpoints
│   │   └── users.py      # /users/* endpoints
│   └── services/
│       └── auth.py       # JWT creation/verification, password hashing
├── alembic/
│   ├── env.py            # Alembic async configuration
│   ├── script.py.mako    # Migration file template
│   └── versions/         # Auto-generated migration scripts
├── tests/
│   └── conftest.py       # Shared pytest fixtures (in-memory SQLite)
├── alembic.ini
├── requirements.txt
├── Dockerfile            # Multi-stage build
├── docker-compose.yml    # App + PostgreSQL + Redis
└── .env.example          # Environment variable template
```

## Environment Variables

See [.env.example](.env.example) for a full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(change me)* | JWT signing secret — use `openssl rand -hex 32` |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_DB` | `auth_service` | Database name |
| `REDIS_HOST` | `localhost` | Redis host |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window size (seconds) |

## Running Tests

```bash
# Install dev dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run the full test suite
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite database and a fake Redis stub — no external services required.

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Downgrade one step
alembic downgrade -1
```

## License

MIT

---

## Join the Discussion

Have ideas or experience to share? Check out our open discussions:

- [Refresh token rotation: worth the complexity?](https://github.com/shahabRDZ/fastapi-auth-service/discussions/28)
- [Rate limiting auth endpoints](https://github.com/shahabRDZ/fastapi-auth-service/discussions/29)

We'd love to hear your thoughts!