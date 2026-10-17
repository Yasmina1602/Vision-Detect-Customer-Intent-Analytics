"""Birinchi super_admin: python scripts/create_superadmin.py --email admin@vision.uz [--password ...]"""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsoli (cp1251)

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402


async def main(email: str, password: str, name: str) -> None:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user:
            user.platform_role = "super_admin"
            user.password_hash = hash_password(password)
            print(f"Mavjud foydalanuvchi super_admin qilindi: {email}")
        else:
            db.add(User(email=email.lower(), password_hash=hash_password(password), full_name=name,
                        platform_role="super_admin"))
            print(f"super_admin yaratildi: {email}")
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--password")
    ap.add_argument("--name", default="Platform Admin")
    a = ap.parse_args()
    pw = a.password or getpass.getpass("Parol: ")
    if len(pw) < 8:
        sys.exit("Parol kamida 8 belgi bo'lishi kerak")
    asyncio.run(main(a.email, pw, a.name))
