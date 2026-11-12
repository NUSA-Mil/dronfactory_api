from typing import Optional
import bleach
from pydantic import BaseModel, ConfigDict, Field, field_validator


def sanitize_xss(v: Optional[str]) -> Optional[str]:
    """[XSS Protection]: Очищает строки от HTML/Script-тегов с помощью bleach"""
    if isinstance(v, str):
        # strip=True вырезает HTML-теги целиком, не искажая кавычки и URL-символы
        cleaned = bleach.clean(v.strip(), tags=[], strip=True)
        return cleaned
    return v


class BaseSchema(BaseModel):
    """Запрет Mass Assignment и безопасная интеграция с ORM"""
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True
    )


class LocalizedText(BaseSchema):
    """Мультиязычное JSONB-поле с XSS-санитизацией"""
    ru: str = Field(..., min_length=1, max_length=1000, description="Наименование/текст на русском")
    en: Optional[str] = Field(None, min_length=1, max_length=1000, description="Наименование/текст на английском")

    @field_validator("ru", "en", mode="before")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)


class LocalizedDescription(BaseSchema):
    """Описание JSONB с XSS-санитизацией"""
    ru: str = Field(..., min_length=1, max_length=5000, description="Описание на русском")
    en: Optional[str] = Field(None, min_length=1, max_length=5000, description="Описание на английском")

    @field_validator("ru", "en", mode="before")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_xss(v)