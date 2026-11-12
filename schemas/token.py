from pydantic import Field
from schemas.common import BaseSchema


class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseSchema):
    sub: str
    role_id: int
    exp: int
    type: str
    jti: str


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)