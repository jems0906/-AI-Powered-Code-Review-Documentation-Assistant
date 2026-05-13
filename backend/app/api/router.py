from fastapi import APIRouter

from app.api.routes import webhooks, reviews, repositories, metrics, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
