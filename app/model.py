from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    username: str
    password_hash: str
    role: str
    is_Active: bool
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
