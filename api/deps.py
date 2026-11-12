from typing import List, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from core.exceptions import ForbiddenException, UnauthorizedException
from core.permissions import (
    ROLE_ADMIN,
    ROLE_CLIENT,
    ROLE_MANAGER,
    ROLE_STOREKEEPER,
)
from core.security import decode_token
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Main dependency to get current authenticated user.
    Decodes JWT, verifies Redis blacklist and returns active User instance.
    """
    payload = await decode_token(token, expected_type="access")
    if not payload:
        raise UnauthorizedException("Invalid, expired or revoked token")

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str or not user_id_str.isdigit():
        raise UnauthorizedException("Invalid user identification in token")

    user_id = int(user_id_str)

    stmt = (
        select(User)
        .options(selectinload(User.role))
        .where(User.user_id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise ForbiddenException("User account is inactive or disabled")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to confirm active status of current user"""
    if not current_user.is_active:
        raise ForbiddenException("User account is inactive")
    return current_user


class RoleCheckerDep:
    """
    Role validation dependency class.
    Relies on get_current_active_user for extra security and resilience.
    """

    def __init__(self, allowed_roles: List[int]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role_id not in self.allowed_roles:
            raise ForbiddenException(
                "Insufficient permissions to perform operation"
            )
        return current_user


# Factory role dependencies for endpoints
get_current_admin = RoleCheckerDep([ROLE_ADMIN])
get_current_manager = RoleCheckerDep([ROLE_MANAGER, ROLE_ADMIN])
get_current_storekeeper = RoleCheckerDep([ROLE_STOREKEEPER, ROLE_ADMIN])
get_current_worker = RoleCheckerDep([ROLE_MANAGER, ROLE_STOREKEEPER, ROLE_ADMIN])
get_current_client_or_staff = RoleCheckerDep(
    [ROLE_CLIENT, ROLE_MANAGER, ROLE_STOREKEEPER, ROLE_ADMIN]
)