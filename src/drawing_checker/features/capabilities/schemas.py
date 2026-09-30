from pydantic import BaseModel


class Capabilities(BaseModel):
    """MAIN kiểm được những gì — để BE biết dòng tiêu chí nào sẽ không được hỗ trợ."""

    version: str
    page_kinds: list[str]
    entity_kinds: list[str]
