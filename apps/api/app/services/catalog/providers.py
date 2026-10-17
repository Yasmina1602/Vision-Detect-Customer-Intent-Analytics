"""Katalog manbalari. Sotuvchi bazasiga hech qachon to'g'ridan-to'g'ri ulanmaymiz — faqat feed/API/push."""
import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.core.errors import AppError

FEED_TIMEOUT = 20
MAX_FEED_BYTES = 50 * 1024 * 1024


def parse_csv(text: str) -> list[dict[str, Any]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]


def parse_json(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("products") or data.get("items") or data.get("data") or []
    if not isinstance(data, list):
        raise AppError("FEED_FORMAT", "JSON feed ro'yxat yoki {products: [...]} bo'lishi kerak")
    return [d for d in data if isinstance(d, dict)]


def parse_google_xml(text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    out = []
    for item in items:
        row: dict[str, Any] = {}
        for child in item:
            tag = child.tag.split("}")[-1]
            row[tag] = (child.text or "").strip()
            row["g:" + tag] = row[tag]
        out.append(row)
    return out


def parse_feed(text: str, fmt: str) -> list[dict[str, Any]]:
    fmt = (fmt or "").lower()
    stripped = text.lstrip()
    if fmt == "xml" or stripped.startswith("<"):
        return parse_google_xml(text)
    if fmt == "json" or stripped[:1] in "[{":
        return parse_json(text)
    return parse_csv(text)


async def fetch_feed(url: str, fmt: str) -> list[dict[str, Any]]:
    if not url.startswith(("http://", "https://")):
        raise AppError("FEED_URL", "Feed URL http(s):// bilan boshlanishi kerak")
    async with httpx.AsyncClient(timeout=FEED_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "VisionDetect-FeedBot/2.0"})
        resp.raise_for_status()
        if len(resp.content) > MAX_FEED_BYTES:
            raise AppError("FEED_TOO_LARGE", "Feed hajmi 50MB dan oshmasligi kerak")
        return parse_feed(resp.text, fmt)
