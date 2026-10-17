"""Sana oralig'i va vaqt zonasi. Saqlash UTC'da, ko'rsatish tenant zonasida (default Asia/Tashkent)."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, text

from app.models import Tenant


@dataclass
class DateRange:
    start_local: date
    end_local: date          # inklyuziv
    start_utc: datetime      # naive UTC
    end_utc: datetime        # eksklyuziv
    offset_min: int          # tenant zonasining UTC'dan farqi

    @property
    def days(self) -> int:
        return (self.end_local - self.start_local).days + 1

    def previous(self) -> "DateRange":
        delta = timedelta(days=self.days)
        return DateRange(self.start_local - delta, self.end_local - delta,
                         self.start_utc - delta, self.end_utc - delta, self.offset_min)

    def local_days(self) -> list[date]:
        return [self.start_local + timedelta(days=i) for i in range(self.days)]


def tenant_tz(tenant: Tenant) -> ZoneInfo:
    try:
        return ZoneInfo(tenant.setting("timezone") or "Asia/Tashkent")
    except Exception:
        return ZoneInfo("Asia/Tashkent")


def make_range(tenant: Tenant, date_from: date | None, date_to: date | None, default_days: int = 30) -> DateRange:
    tz = tenant_tz(tenant)
    today = datetime.now(tz).date()
    end = min(date_to or today, today)
    start = date_from or end - timedelta(days=default_days - 1)
    if start > end:
        start, end = end, start
    if (end - start).days > 366:
        start = end - timedelta(days=366)

    def to_utc(d: date) -> datetime:
        return datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)

    offset = int(datetime.now(tz).utcoffset().total_seconds() // 60)  # type: ignore[union-attr]
    return DateRange(start, end, to_utc(start), to_utc(end + timedelta(days=1)), offset)


def local_date_expr(col, offset_min: int):
    """DATE(col + offset) — MySQL'da tz jadvallari shart emas."""
    return func.date(func.date_add(col, text(f"INTERVAL {int(offset_min)} MINUTE")))


def pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


def delta_pct(cur: float, prev: float) -> float | None:
    if not prev:
        return None
    return round((cur - prev) / prev * 100, 1)
