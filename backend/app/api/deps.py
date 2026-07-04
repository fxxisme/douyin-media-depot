from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import require_auth
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(require_auth)]
