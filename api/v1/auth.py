from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_user
from core.database import get_db
from core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from core.logger import log_audit
from core.rate_limit import check_rate_limit
from core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from models.user import User
from schemas.token import RefreshTokenRequest, Token
from schemas.user import (
    OTPRequest,
    ResetPasswordRequest,
    UserCreate,
    UserResponse,
    VerifyRegistrationRequest,
)
from services.otp_service import otp_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя по Email",
)
async def register(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(request, max_requests=3, window_seconds=60)
    client_ip = request.client.host if request.client else "127.0.0.1"
    email_str = str(user_in.email)

    existing_user_stmt = select(User).where(User.email == email_str)
    result = await db.execute(existing_user_stmt)
    if result.scalar_one_or_none():
        raise BadRequestException("Пользователь с таким email уже существует")

    # Берём role_id из входящего JSON (если не передан — дефолт 1)
    target_role_id = user_in.role_id if user_in.role_id is not None else 1

    db_user = User(
        email=email_str,
        password_hash=get_password_hash(user_in.password),
        phone_number=user_in.phone_number,
        full_name=user_in.full_name,
        role_id=target_role_id,
        is_active=True,
        is_verified=True,
        language="system",
        theme_mode="system",
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    user_id_int = int(getattr(db_user, "user_id"))

    await otp_service.generate_otp(email_str)

    log_audit(
        user_id=user_id_int,
        ip_address=client_ip,
        category="AUTH",
        action="REGISTER",
        details=f"Пользователь {email_str} зарегистрирован с ролью {target_role_id}, отправлен OTP",
    )

    stmt = select(User).options(selectinload(User.role)).where(User.user_id == user_id_int)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.post(
    "/verify-registration",
    response_model=Token,
    summary="Подтверждение регистрации по OTP с автоматическим входом",
)
async def verify_registration(
    req_in: VerifyRegistrationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    clean_email = str(req_in.email).strip().lower()
    clean_code = req_in.otp_code.strip()
    client_ip = request.client.host if request.client else "127.0.0.1"

    is_valid = await otp_service.verify_otp(clean_email, clean_code)
    if not is_valid:
        raise BadRequestException("Неверный или просроченный OTP-код")

    stmt = select(User).where(User.email == clean_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise NotFoundException("Пользователь не найден")

    user.is_verified = True
    await db.commit()
    await db.refresh(user)

    user_id_int = int(getattr(user, "user_id"))
    role_id_int = int(getattr(user, "role_id"))

    access_token = create_access_token(subject=user_id_int, role_id=role_id_int)
    refresh_token, _ = create_refresh_token(subject=user_id_int)

    log_audit(
        user_id=user_id_int,
        ip_address=client_ip,
        category="AUTH",
        action="VERIFY_AND_LOGIN",
        details=f"Успешная верификация почты и вход для {clean_email}",
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/request-otp",
    status_code=status.HTTP_200_OK,
    summary="Запрос/повторная отправка 6-значного OTP-кода",
)
async def request_otp(
    otp_req: OTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(request, max_requests=2, window_seconds=60)
    email_str = str(otp_req.email)

    stmt = select(User).where(User.email == email_str)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        return {"message": "Если аккаунт существует, OTP код отправлен на почту"}

    await otp_service.generate_otp(email_str)
    return {"message": f"OTP-код успешно отправлен на {email_str}"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Сброс пароля по 6-значному OTP-коду",
)
async def reset_password(
    req_in: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    clean_email = str(req_in.email).strip().lower()
    clean_code = req_in.otp_code.strip()

    is_valid = await otp_service.verify_otp(clean_email, clean_code)
    if not is_valid:
        raise BadRequestException("Неверный или просроченный OTP-код")

    stmt = select(User).where(User.email == clean_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise NotFoundException("Пользователь не найден")

    user.password_hash = get_password_hash(req_in.new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение профиля текущего авторизованного пользователя",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_int = int(getattr(current_user, "user_id"))
    stmt = select(User).options(selectinload(User.role)).where(User.user_id == user_id_int)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.post(
    "/login",
    response_model=Token,
    summary="Аутентификация по Email или Телефону",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(request, max_requests=5, window_seconds=60)
    client_ip = request.client.host if request.client else "127.0.0.1"

    login_input = form_data.username.strip()
    stmt = select(User).where((User.email == login_input) | (User.phone_number == login_input))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, str(getattr(user, "password_hash"))):
        log_audit(
            user_id=None,
            ip_address=client_ip,
            category="AUTH",
            action="LOGIN_FAILED",
            details=f"Неудачная попытка входа для: {login_input}",
        )
        raise UnauthorizedException("Неверный email/телефон или пароль")

    if not user.is_active:
        raise UnauthorizedException("Учетная запись неактивна")

    user_id_int = int(getattr(user, "user_id"))
    role_id_int = int(getattr(user, "role_id"))

    access_token = create_access_token(subject=user_id_int, role_id=role_id_int)
    refresh_token, _ = create_refresh_token(subject=user_id_int)

    log_audit(
        user_id=user_id_int,
        ip_address=client_ip,
        category="AUTH",
        action="LOGIN_SUCCESS",
        details="Успешный вход в систему",
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Ротация Refresh-токена",
)
async def refresh_tokens(
    token_req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await decode_token(token_req.refresh_token, expected_type="refresh")
    if not payload:
        raise UnauthorizedException("Невалидный или просроченный refresh-токен")

    user_id = int(payload["sub"])
    jti = str(payload["jti"])
    exp = float(payload["exp"])

    ttl = max(1, int(exp - (request.state.time if hasattr(request.state, "time") else 3600)))
    await blacklist_token(jti, ttl_seconds=ttl)

    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("Пользователь заблокирован или не найден")

    user_id_int = int(getattr(user, "user_id"))
    role_id_int = int(getattr(user, "role_id"))

    new_access_token = create_access_token(subject=user_id_int, role_id=role_id_int)
    new_refresh_token, _ = create_refresh_token(subject=user_id_int)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из системы (отзыв Access токена)",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ")[1]
        payload = await decode_token(raw_token, expected_type="access")
        if payload and "jti" in payload:
            await blacklist_token(str(payload["jti"]), ttl_seconds=1800)

    log_audit(
        user_id=int(getattr(current_user, "user_id")),
        ip_address=client_ip,
        category="AUTH",
        action="LOGOUT",
        details="Пользователь вышел из системы",
    )