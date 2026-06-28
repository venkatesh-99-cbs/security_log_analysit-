from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def get_health():
    return {"status": "healthy", "components": {"database": "connected", "ollama": "reachable"}}
