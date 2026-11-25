from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import check_db_connection, get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Check application readiness and database connectivity."""
    try:
        is_connected = check_db_connection(db)
    except SQLAlchemyError:
        is_connected = False

    if not is_connected:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )
    return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
