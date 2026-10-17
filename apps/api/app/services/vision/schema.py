from pydantic import BaseModel, Field, field_validator

from app.services.matching.normalizer import normalize_category, normalize_color, normalize_type


class VisionResult(BaseModel):
    """AI faqat shu strukturali maydonlarni qaytaradi; qiymatlar whitelist/normalizatsiyadan o'tadi."""
    category: str = "boshqa"
    color: str | None = None
    type: str | None = None
    style: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    search_query: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("category", mode="before")
    @classmethod
    def _cat(cls, v):
        return normalize_category(str(v or ""))

    @field_validator("color", mode="before")
    @classmethod
    def _color(cls, v):
        return normalize_color(str(v)) if v else None

    @field_validator("type", mode="before")
    @classmethod
    def _type(cls, v):
        return normalize_type(str(v)) if v else None

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, v):
        if not isinstance(v, list):
            return []
        return [str(t)[:40].strip().lower() for t in v if str(t).strip()][:10]

    @field_validator("search_query", "style", mode="before")
    @classmethod
    def _short(cls, v):
        return str(v)[:120].strip() if v else ""
