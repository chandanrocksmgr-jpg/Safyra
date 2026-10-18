from pydantic import BaseModel, Field


class VerificationConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=300)


class VerificationResponse(BaseModel):
    verified: bool
    claimed_orders: int = 0


class VerificationSendResponse(BaseModel):
    accepted: bool = True