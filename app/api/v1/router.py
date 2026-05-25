"""V1 API router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, authors, books, borrowing, categories, health, members

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(books.router)
api_router.include_router(authors.router)
api_router.include_router(categories.router)
api_router.include_router(members.router)
api_router.include_router(borrowing.router)
