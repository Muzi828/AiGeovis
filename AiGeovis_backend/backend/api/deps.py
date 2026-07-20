"""Shared FastAPI dependencies for API routers."""
from __future__ import annotations

from typing import Dict

from fastapi import HTTPException

from core.sessions import sessions


def get_session(session_id: str) -> Dict:
    """Return an in-memory session or raise 404."""
    sess = sessions.get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess
