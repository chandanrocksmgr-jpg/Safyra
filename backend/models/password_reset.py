from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    accepted: bool = True


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=200)
    new_password: str
