"""Stub auth router — extend with OAuth / JWT as needed."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def auth_status():
    return {"authenticated": True, "note": "Add OAuth/JWT integration here"}
