from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int

class UserOut(BaseModel):
    id: int
    username: str
    role_id: int
    is_active: bool

    class Config:
        orm_mode = True
