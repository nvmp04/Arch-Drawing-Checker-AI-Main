from fastapi import HTTPException, status


def not_implemented(name: str) -> HTTPException:
    """Route chưa hiện thực trả 501 kèm tên — cùng tinh thần ADR-09 của BE."""
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"code": "NOT_IMPLEMENTED", "message": f"{name} chưa hiện thực"},
    )
