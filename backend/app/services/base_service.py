from fastapi import HTTPException


class BaseService:
    """
    All services inherit from this.
    user_id is injected at construction time from auth middleware.
    Never query without user context.
    """

    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id

    def _raise_forbidden(self, entity_type: str = "resource") -> None:
        raise HTTPException(
            status_code=403,
            detail=f"{entity_type}_not_found_or_forbidden",
        )

    def _assert_ownership(self, record: dict, entity_type: str = "resource") -> None:
        if not record or str(record.get("user_id")) != str(self.user_id):
            self._raise_forbidden(entity_type)
