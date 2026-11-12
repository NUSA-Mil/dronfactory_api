import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.config import settings
from core.logger import app_logger
from core.rate_limit import redis_client

OTP_EXPIRE_SECONDS = 300  # 5 минут


class OTPService:
    @staticmethod
    def generate_code() -> str:
        return f"{random.randint(100000, 999999)}"

    async def generate_otp(self, email: str) -> str:
        code = self.generate_code()
        redis_key = f"otp:{email}"

        # Сохраняем OTP в Redis на 5 минут
        await redis_client.setex(redis_key, OTP_EXPIRE_SECONDS, code)

        # Выводим OTP в консоль разработчика для отладки
        app_logger.info(f"=== [OTP GENERATED] === Email: {email} | Code: {code}")

        # Отправляем письмо в Mailpit
        await self.send_otp_email(email, code)
        return code

    async def verify_otp(self, email: str, code: str) -> bool:
        redis_key = f"otp:{email}"
        stored_code = await redis_client.get(redis_key)

        if not stored_code:
            return False

        if stored_code == code:
            await redis_client.delete(redis_key)
            return True
        return False

    async def send_otp_email(self, to_email: str, code: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = "Код подтверждения регистрации — DronFactory"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #1a1a1a; color: #ffffff; padding: 20px;">
                <div style="max-width: 500px; margin: 0 auto; background: #2a2a2a; padding: 30px; border-radius: 8px;">
                    <h2 style="color: #00e676; text-align: center;">DronFactory</h2>
                    <p>Ваш код подтверждения для входа в систему:</p>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; text-align: center; color: #00e676; padding: 15px; background: #111; border-radius: 4px; margin: 20px 0;">
                        {code}
                    </div>
                    <p style="font-size: 12px; color: #888;">Код действителен в течение 5 минут. Если вы не запрашивали код, проигнорируйте это письмо.</p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            # Прямая синхронная отправка на 127.0.0.1:1025 для гарантированной доставки под Windows
            with smtplib.SMTP(host=settings.SMTP_HOST, port=settings.SMTP_PORT, timeout=5) as server:
                server.send_message(msg)
            app_logger.info(f"Письмо с OTP успешно доставлено в Mailpit для {to_email}")
        except Exception as e:
            app_logger.error(f"Ошибка отправки почты в Mailpit ({settings.SMTP_HOST}:{settings.SMTP_PORT}): {e}")


otp_service = OTPService()