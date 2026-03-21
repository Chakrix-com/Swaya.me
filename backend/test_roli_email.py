import asyncio
import os
import sys

# Add the backend directory to Python path so we can import modules
sys.path.append("/home/vinay/Swaya.me/backend")

from core.auth.email_service import send_verification_email
from dotenv import load_dotenv

load_dotenv("/home/vinay/Swaya.me/backend/.env")

async def force_send():
    print(f"SMTP HOST: {os.getenv('SMTP_HOST')}")
    print(f"SMTP PORT: {os.getenv('SMTP_PORT')}")
    print(f"SMTP USER: {os.getenv('SMTP_USER')}")
    print(f"FRONTEND URL: {os.getenv('FRONTEND_URL', 'Using settings fallback')}")
    print("Attempting to send real verification email to roliverma06@gmail.com...")
    
    success = await send_verification_email(
        email="roliverma06@gmail.com", 
        token="REDACTED_EMAIL_TOKEN", 
        name="Roli Verma"
    )
    print(f"FastMail Success Boolean: {success}")

if __name__ == "__main__":
    asyncio.run(force_send())
