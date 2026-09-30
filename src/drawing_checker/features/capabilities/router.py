from fastapi import APIRouter

from drawing_checker.common.errors import not_implemented
from drawing_checker.features.capabilities.schemas import Capabilities

router = APIRouter(prefix="/v1", tags=["capabilities"])


@router.get("/capabilities", response_model=Capabilities)
async def get_capabilities() -> Capabilities:
    raise not_implemented("capabilities.get")
