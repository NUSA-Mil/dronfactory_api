from typing import List
from fastapi import HTTPException, status

ROLE_CLIENT = 1
ROLE_MANAGER = 2
ROLE_STOREKEEPER = 3
ROLE_ADMIN = 4


class RoleChecker:
    """[Пункт 5]: Валидация актуальных прав через БД"""
    def __init__(self, allowed_roles: List[int]):
        self.allowed_roles = allowed_roles

    def check_user_role(self, user_role_id: int):
        if user_role_id not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции"
            )


def check_owner_or_worker(resource_user_id: int, current_user_id: int, current_user_role_id: int):
    """
    Защита от IDOR/BOLA:
    Клиент может читать/менять ТОЛЬКО свои заказы и профиль.
    Рабочий состав (Менеджер/Админ) может просматривать чужие.
    """
    if current_user_role_id == ROLE_CLIENT and resource_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к чужим ресурсам запрещен (IDOR Protection)"
        )


require_client = RoleChecker([ROLE_CLIENT, ROLE_MANAGER, ROLE_ADMIN])
require_manager = RoleChecker([ROLE_MANAGER, ROLE_ADMIN])
require_storekeeper = RoleChecker([ROLE_STOREKEEPER, ROLE_ADMIN])
require_worker = RoleChecker([ROLE_MANAGER, ROLE_STOREKEEPER, ROLE_ADMIN])
require_admin = RoleChecker([ROLE_ADMIN])