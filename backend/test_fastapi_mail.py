import asyncio
from core.auth.email_service import send_verification_email
from dotenv import load_dotenv

load_dotenv()

async def test():
    print("Sending test email...")
    success = await send_verification_email("info@chakrix.com", "test-token-123", "Test User")
    print(f"Success: {success}")

if __name__ == "__main__":
    asyncio.run(test())
