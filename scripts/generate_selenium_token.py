"""
Generate a valid JWT access token for Selenium testing.
Queries the DB for the host user, builds a token using the same secret + payload
as the login endpoint. No password needed — we own the server and the JWT secret.

Usage:
    python scripts/generate_selenium_token.py [email]
    # default email: meetnishant@gmail.com
"""
import asyncio
import sys

sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from dotenv import load_dotenv
load_dotenv('/home/vinay/Swaya.me/backend/.env')

from core.config.settings import settings  # noqa: E402
from core.security.jwt import create_access_token  # noqa: E402
from persistence.database_async import AsyncSessionLocal  # noqa: E402
from sqlalchemy import select  # noqa: E402
from persistence.models.core import User, Tenant  # noqa: E402


async def main():
    email = sys.argv[1] if len(sys.argv) > 1 else 'meetnishant@gmail.com'
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one()
        token = create_access_token({
            'sub': str(user.id),
            'email': user.email,
            'tenant_id': tenant.id,
            'tier': tenant.tier.value,
            'role': user.role.value,
        })
        print(token)


asyncio.run(main())
