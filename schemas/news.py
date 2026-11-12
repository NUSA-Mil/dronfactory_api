from datetime import datetime
from typing import Optional
from schemas.common import BaseSchema, LocalizedText, LocalizedDescription


class NewsCreate(BaseSchema):
    title: LocalizedText
    content: LocalizedDescription


class NewsUpdate(BaseSchema):
    title: Optional[LocalizedText] = None
    content: Optional[LocalizedDescription] = None


class NewsResponse(BaseSchema):
    news_id: int
    title: LocalizedText
    content: LocalizedDescription
    author_id: Optional[int] = None
    created_at: datetime