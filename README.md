# Library Management System

A FastAPI-based library management application with JWT authentication, book cataloging, member management, and a complete borrowing/return system.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL + SQLAlchemy 2.0 + Alembic
- **Auth**: JWT (access + refresh tokens)
- **Deployment**: Docker, docker-compose
- **Package Manager**: uv

## Project Structure

```
library-management/
├── alembic/              # Database migrations
├── app/
│   ├── api/v1/endpoints/ # Route handlers
│   ├── core/             # Config, security, logging
│   ├── db/               # Database session & base
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic layer
│   └── main.py           # App entry point
├── docker-compose.yml    # Local infrastructure
├── Dockerfile            # Production build
└── Makefile              # Common commands
```

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start database
docker compose up -d db

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SECRET_KEY` | JWT signing key | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |

## Branch Strategy

- **`master`** — Production-ready code. Deployed to production.
- **`develop`** — Active development. Feature branches merge here.

### Workflow

```
feature/xxx  →  develop  →  master
```

## API Endpoints

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/refresh` |
| Books | `GET/POST /books`, `GET/PUT/DELETE /books/{id}` |
| Authors | `GET/POST /authors`, `GET/PUT/DELETE /authors/{id}` |
| Categories | `GET/POST /categories`, `GET/PUT/DELETE /categories/{id}` |
| Members | `GET/POST /members`, `GET/PUT/DELETE /members/{id}` |
| Borrowing | `POST /borrow`, `POST /return/{record_id}` |

## Commands

```bash
make install    # Install dependencies
make migrate    # Run migrations
make dev        # Start dev server
make lint       # ruff check
make test       # Run tests
```
